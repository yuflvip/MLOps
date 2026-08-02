#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/configs"
ATC_SETENV="/usr/local/Ascend/ascend-toolkit/svp_latest/x86_64-linux/script/setenv.sh"

MODEL_PATH=""
IMAGE_LIST_PATH=""
INPUT_SHAPE=""
INSERT_OP_CONF="${CONFIG_DIR}/insert_op.cfg"
OUTPUT_PREFIX=""
SOC_VERSION="SS928V100"
COMPILE_MODE="6"
OUTPUT_TYPE="FP32"
QUANT_MODE="1"
HIGH_PRECISION_LAYER=""
ONLINE_MODEL_TYPE="0"
DRY_RUN=0

usage() {
    cat <<'EOF'
用法：
  bash export_svpnnn_om.sh --model model.onnx --image-list ref_img_list.txt [参数]

参数：
  --model <路径>
  --image-list <路径>
  --input-shape <input_name:n,c,h,w>
  --insert-op-conf <路径>
  --output <OM输出前缀>
  --soc-version <值>
  --compile-mode <值>
  --output-type <值>
  --quant-mode <值>
  --high-precision-layer <值>
  --online-model-type <值>
  --dry-run
EOF
}

die() {
    printf '错误: %s\n' "$1" >&2
    exit 1
}

absolute_path() {
    python3 - "$1" <<'PY'
import os
import sys
print(os.path.abspath(sys.argv[1]))
PY
}

parse_onnx_input_shape() {
    python3 - "$1" <<'PY'
import sys

try:
    import onnx
except ModuleNotFoundError:
    sys.exit(2)

model = onnx.load(sys.argv[1])
if not model.graph.input:
    sys.exit(3)
tensor = model.graph.input[0]
dims = []
for dim in tensor.type.tensor_type.shape.dim:
    if not dim.HasField("dim_value"):
        sys.exit(4)
    dims.append(str(dim.dim_value))
if len(dims) != 4:
    sys.exit(5)
print(f"{tensor.name}:{','.join(dims)}")
PY
}

ensure_atc_env() {
    if command -v atc >/dev/null 2>&1; then
        return
    fi
    [[ -f "${ATC_SETENV}" ]] || die "未找到 Ascend Toolkit 环境脚本：${ATC_SETENV}"
    local restore_nounset=0
    if [[ $- == *u* ]]; then
        restore_nounset=1
        set +u
    fi
    # shellcheck disable=SC1090
    source "${ATC_SETENV}" >/dev/null 2>&1 || die "加载 Ascend Toolkit 环境失败"
    if [[ ${restore_nounset} -eq 1 ]]; then
        set -u
    fi
    command -v atc >/dev/null 2>&1 || die "加载环境后仍未找到 atc"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL_PATH="${2:-}"; shift 2 ;;
        --image-list) IMAGE_LIST_PATH="${2:-}"; shift 2 ;;
        --input-shape) INPUT_SHAPE="${2:-}"; shift 2 ;;
        --insert-op-conf) INSERT_OP_CONF="${2:-}"; shift 2 ;;
        --output) OUTPUT_PREFIX="${2:-}"; shift 2 ;;
        --soc-version) SOC_VERSION="${2:-}"; shift 2 ;;
        --compile-mode) COMPILE_MODE="${2:-}"; shift 2 ;;
        --output-type) OUTPUT_TYPE="${2:-}"; shift 2 ;;
        --quant-mode) QUANT_MODE="${2:-}"; shift 2 ;;
        --high-precision-layer) HIGH_PRECISION_LAYER="${2:-}"; shift 2 ;;
        --online-model-type) ONLINE_MODEL_TYPE="${2:-}"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) die "未知参数：$1" ;;
    esac
done

[[ -n "${MODEL_PATH}" ]] || die "--model 不能为空"
[[ -n "${IMAGE_LIST_PATH}" ]] || die "--image-list 不能为空"
[[ -n "${OUTPUT_PREFIX}" ]] || die "--output 不能为空"
[[ -n "${SOC_VERSION}" ]] || die "--soc-version 不能为空"
[[ -n "${COMPILE_MODE}" ]] || die "--compile-mode 不能为空"
[[ -n "${QUANT_MODE}" ]] || die "--quant-mode 不能为空"
[[ -n "${ONLINE_MODEL_TYPE}" ]] || die "--online-model-type 不能为空"

MODEL_PATH="$(absolute_path "${MODEL_PATH}")"
IMAGE_LIST_PATH="$(absolute_path "${IMAGE_LIST_PATH}")"
INSERT_OP_CONF="$(absolute_path "${INSERT_OP_CONF}")"
OUTPUT_PREFIX="$(absolute_path "${OUTPUT_PREFIX}")"

[[ -f "${MODEL_PATH}" ]] || die "ONNX模型不存在：${MODEL_PATH}"
[[ -f "${IMAGE_LIST_PATH}" ]] || die "量化图片列表不存在：${IMAGE_LIST_PATH}"
[[ -s "${IMAGE_LIST_PATH}" ]] || die "量化图片列表为空：${IMAGE_LIST_PATH}"
[[ -f "${INSERT_OP_CONF}" ]] || die "AIPP配置不存在：${INSERT_OP_CONF}"

if [[ -z "${INPUT_SHAPE}" ]]; then
    set +e
    INPUT_SHAPE="$(parse_onnx_input_shape "${MODEL_PATH}")"
    parse_code=$?
    set -e
    if [[ ${parse_code} -ne 0 ]]; then
        die "无法自动解析ONNX静态输入Shape，请在页面填写 --input-shape"
    fi
fi
[[ "${INPUT_SHAPE}" == *:* ]] || die "--input-shape 格式应为 input_name:n,c,h,w"

ATC_COMMAND=(
    atc
    --framework=5
    --model="${MODEL_PATH}"
    --input_shape="${INPUT_SHAPE}"
    --insert_op_conf="${INSERT_OP_CONF}"
    --output="${OUTPUT_PREFIX}"
    --image_list="${IMAGE_LIST_PATH}"
    --soc_version="${SOC_VERSION}"
    --compile_mode="${COMPILE_MODE}"
    --quant_mode="${QUANT_MODE}"
    --online_model_type="${ONLINE_MODEL_TYPE}"
    --weight_quant_per_channel=1
    --matmul_per_channel_enable=0
    --all_batch_quant_together_enable=1
    --softmax_optimize_enable=1
)

if [[ -n "${OUTPUT_TYPE}" ]]; then
    ATC_COMMAND+=(--output_type="${OUTPUT_TYPE}")
fi
if [[ -n "${HIGH_PRECISION_LAYER}" ]]; then
    ATC_COMMAND+=(--high_precision_layer="${HIGH_PRECISION_LAYER}")
fi

printf 'ONNX转海思3403参数：\n'
printf '  model                : %s\n' "${MODEL_PATH}"
printf '  image_list           : %s\n' "${IMAGE_LIST_PATH}"
printf '  input_shape          : %s\n' "${INPUT_SHAPE}"
printf '  insert_op_conf       : %s\n' "${INSERT_OP_CONF}"
printf '  output               : %s.om\n' "${OUTPUT_PREFIX}"
printf '  soc_version          : %s\n' "${SOC_VERSION}"
printf '  compile_mode         : %s\n' "${COMPILE_MODE}"
printf '  output_type          : %s\n' "${OUTPUT_TYPE:-<空>}"
printf '  quant_mode           : %s\n' "${QUANT_MODE}"
printf '  high_precision_layer : %s\n' "${HIGH_PRECISION_LAYER:-<空>}"
printf '  online_model_type    : %s\n' "${ONLINE_MODEL_TYPE}"
printf 'ATC命令：\n'
printf '  '
printf '%q ' "${ATC_COMMAND[@]}"
printf '\n'

if [[ ${DRY_RUN} -eq 1 ]]; then
    printf 'dry-run完成，未生成OM文件。\n'
    exit 0
fi

ensure_atc_env
mkdir -p "$(dirname "${OUTPUT_PREFIX}")"

start_time="$(date +%s)"
"${ATC_COMMAND[@]}"
elapsed="$(( $(date +%s) - start_time ))"
[[ -f "${OUTPUT_PREFIX}.om" ]] || die "ATC返回成功，但未找到输出文件：${OUTPUT_PREFIX}.om"
printf 'ONNX转OM成功：%s.om\n' "${OUTPUT_PREFIX}"
printf '转换耗时：%s秒\n' "${elapsed}"
