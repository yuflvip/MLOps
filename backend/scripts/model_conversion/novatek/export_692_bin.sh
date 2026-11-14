#!/usr/bin/env bash
set -euo pipefail

# 默认参数统一在此维护，帮助文本自动引用这些值。
EXP_DIR=''
QUANT_DIR=''
TOOL_DIR='/mnt/yolo_tool/novatek/release_v04.01.250807.00'
IMAGE='ubuntu20p04:202407013'
MODEL='best.onnx'
CHIP=690
OP_MODE=2
BIT_MODE=1
QUAN_SCHEME=1
USE_ONNX=true
STRIPE_PERFMODE=1
VLC_EN=1
DRY_RUN=0


usage() {
    cat <<EOF
用法：bash export_692_bin.sh --exp-dir DIR --quant-dir DIR [选项]

必填：
  --exp-dir DIR          实验目录，挂载到 /exp
  --quant-dir DIR        含 config/ 和 ref_img_list.txt 的量化目录，按原绝对路径只读挂载
选项：
  --model NAME          实验目录内的 ONNX 相对路径（默认 ${MODEL}）
  --tool-dir DIR        默认 ${TOOL_DIR}
  --image NAME          默认 ${IMAGE}
  --chip VALUE          默认 ${CHIP}（692 模型沿用已验证的芯片参数）
  --op-mode VALUE       默认 ${OP_MODE}
  --bit-mode VALUE      默认 ${BIT_MODE} 1-8w8a/2-16a16w/3-8w16a/4-16W8A
  --quan-scheme VALUE   默认 ${QUAN_SCHEME} 0-按张量/1-权重按通道/2-权重和激活均按通道/3-通道+SmoothQuant
  --use-onnx [BOOL]     默认 ${USE_ONNX}；可传 true/false 或 1/0
  --stripe-perfmode N   默认 ${STRIPE_PERFMODE}
  --vlc-en VALUE        默认 ${VLC_EN}；仅支持 0/1，也可使用 --vlc-en=1
  --dry-run             校验本地路径并打印命令，不启动 Docker 或写文件
  -h, --help            显示帮助

脚本复现手动流程：将 ONNX 复制为 /exp/novaic_output/deploy_float.onnx，
然后执行 compiler.V30。配置须指向 /exp/novaic_output，图片列表中的路径
须在容器内可访问。脚本不改写配置、不猜测最终 bin 文件名。
重复执行会更新 novaic_output 内文件；请勿针对同一实验目录并发执行。
EOF
}

die() { printf '错误: %s\n' "$*" >&2; exit 1; }

while (( $# )); do
    case "$1" in
        -h|--help) usage; exit 0 ;;
        --dry-run) DRY_RUN=1; shift; continue ;;
        --vlc-en=*) VLC_EN="${1#*=}"; shift; continue ;;
        --use-onnx)
            USE_ONNX=true
            if (( $# > 1 )) && [[ "$2" != --* ]]; then
                USE_ONNX="$2"; shift
            fi
            shift; continue ;;
        --exp-dir|--quant-dir|--tool-dir|--image|--model|--chip|--op-mode|--bit-mode|--quan-scheme|--stripe-perfmode|--vlc-en)
            (( $# >= 2 )) && [[ -n "$2" && "$2" != --* ]] || die "$1 缺少参数值"
            case "$1" in
                --exp-dir) EXP_DIR="$2" ;;
                --quant-dir) QUANT_DIR="$2" ;;
                --tool-dir) TOOL_DIR="$2" ;;
                --image) IMAGE="$2" ;;
                --model) MODEL="$2" ;;
                --chip) CHIP="$2" ;;
                --op-mode) OP_MODE="$2" ;;
                --bit-mode) BIT_MODE="$2" ;;
                --quan-scheme) QUAN_SCHEME="$2" ;;
                --stripe-perfmode) STRIPE_PERFMODE="$2" ;;
                --vlc-en) VLC_EN="$2" ;;
            esac
            shift 2 ;;
        *) die "未知参数：$1" ;;
    esac
done

[[ -n "$EXP_DIR" ]] || die '--exp-dir 必填'
[[ -n "$QUANT_DIR" ]] || die '--quant-dir 必填'
[[ "$VLC_EN" == 0 || "$VLC_EN" == 1 ]] || die '--vlc-en 必须为 0 或 1'
for value in "$CHIP" "$OP_MODE" "$BIT_MODE" "$QUAN_SCHEME" "$STRIPE_PERFMODE"; do
    [[ "$value" =~ ^[0-9]+$ ]] || die "编译数值参数必须为非负整数：$value"
done
case "$USE_ONNX" in
    true|1) USE_ONNX=true ;;
    false|0) USE_ONNX=false ;;
    *) die '--use-onnx 必须为 true/false 或 1/0' ;;
esac
for directory in "$EXP_DIR" "$QUANT_DIR" "$TOOL_DIR"; do
    [[ -d "$directory" ]] || die "目录不存在：$directory"
done
EXP_DIR=$(realpath -- "$EXP_DIR")
QUANT_DIR=$(realpath -- "$QUANT_DIR")
TOOL_DIR=$(realpath -- "$TOOL_DIR")
for directory in "$EXP_DIR" "$QUANT_DIR" "$TOOL_DIR"; do
    [[ "$directory" != *,* ]] || die "Docker 挂载路径不支持逗号：$directory"
done
[[ "$MODEL" != /* ]] || die '--model 必须是实验目录内的相对路径'
MODEL_PATH=$(realpath -m -- "$EXP_DIR/$MODEL")
[[ "$MODEL_PATH" == "$EXP_DIR/"* && "$MODEL_PATH" == *.onnx && -s "$MODEL_PATH" ]] || die '源 ONNX 必须是实验目录内的非空文件'
MODEL=${MODEL_PATH#"$EXP_DIR/"}
[[ -d "$QUANT_DIR/config" && -s "$QUANT_DIR/ref_img_list.txt" ]] || die '量化目录缺少 config/ 或非空 ref_img_list.txt'
TOOL_TARGET='/release_v04.01.250807.00'
COMPILER_REL='ai_tool/novatek/novaic/toolchain/closeprefix/bin/compiler.V30'
[[ -x "$TOOL_DIR/$COMPILER_REL" ]] || die "编译器不存在或不可执行：$TOOL_DIR/$COMPILER_REL"

compiler_args=(--config-dir "$QUANT_DIR" --pattern-name . --chip "$CHIP"
    --op-mode "$OP_MODE" --bit-mode "$BIT_MODE" --quan-scheme "$QUAN_SCHEME")
[[ "$USE_ONNX" == false ]] || compiler_args+=(--use-onnx)
compiler_args+=(--stripe-perfmode "$STRIPE_PERFMODE")
compiler_args+=("--vlc-en=$VLC_EN")

# 参数通过位置参数传给容器，不将用户输入拼入 shell 代码。
container_script='
set -euo pipefail
model=$1
tool=$2
compiler=$3
shift 3
mkdir -p /exp/novaic_output
cp -- "/exp/$model" /exp/novaic_output/deploy_float.onnx
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:+$LD_LIBRARY_PATH:}$tool/ai_tool/novatek/novaic/toolchain/repo/proprietary/opencv/lib"
exec "$tool/$compiler" "$@"
'
command=(docker run --rm
    --mount "type=bind,source=$TOOL_DIR,target=$TOOL_TARGET"
    --mount "type=bind,source=$EXP_DIR,target=/exp"
    --mount "type=bind,source=$QUANT_DIR,target=$QUANT_DIR,readonly"
    "$IMAGE" bash -c "$container_script" novatek692
    "$MODEL" "$TOOL_TARGET" "$COMPILER_REL" "${compiler_args[@]}")
printf '执行命令：\n'
printf '%q ' "${command[@]}"
printf '\n'
if (( DRY_RUN )); then exit 0; fi
command -v docker >/dev/null 2>&1 || die '未安装 docker'
"${command[@]}"
printf '编译器执行完成，输出目录：%s/novaic_output（请检查最终部署 bin）\n' "$EXP_DIR"
