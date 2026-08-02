#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/configs"
CONDA_SH="/root/miniconda3/etc/profile.d/conda.sh"
CONDA_ENV="ascend-env"
ATC_SETENV="/usr/local/Ascend/ascend-toolkit/latest/x86_64-linux/bin/setenv.bash"

MODEL_PATH=""
INPUT_SHAPE=""
INSERT_OP_CONF="${CONFIG_DIR}/insert_op_nnn_hgnet.cfg"
OUTPUT_PREFIX=""
SOC_VERSION="OPTG"
ENABLE_SINGLE_STREAM="true"
ENABLE_SMALL_CHANNEL="1"
DRY_RUN=0

usage() {
    cat <<'EOF'
用法：
  bash export_nnn_om.sh --model model.onnx --input-shape images:1,3,224,224 --output output/best [参数]

参数：
  --model <路径>
  --input-shape <input_name:n,c,h,w>
  --insert-op-conf <路径>
  --output <OM输出前缀>
  --soc-version <值>
  --enable-single-stream <true|false>
  --enable-small-channel <0|1>
  --dry-run
EOF
}

die() {
    printf '错误: %s\n' "$1" >&2
    exit 1
}

absolute_path() {
    realpath -m -- "$1"
}

load_ascend_env() {
    [[ -f "${CONDA_SH}" ]] || die "未找到 Conda 初始化脚本：${CONDA_SH}"
    [[ -f "${ATC_SETENV}" ]] || die "未找到 Ascend Toolkit 环境脚本：${ATC_SETENV}"

    set +u
    # shellcheck disable=SC1090
    source "${CONDA_SH}"
    conda activate "${CONDA_ENV}" || die "激活 Conda 环境失败：${CONDA_ENV}"
    # shellcheck disable=SC1090
    source "${ATC_SETENV}" >/dev/null 2>&1 || die "加载 Ascend Toolkit 环境失败"
    set -u

    export NPU_INCLUDE_PATH="/usr/local/Ascend/ascend-toolkit/latest/acllib/include/acl"
    export NPU_LIB_PATH="/usr/local/Ascend/ascend-toolkit/latest/acllib/lib64/stub"

    command -v atc >/dev/null 2>&1 || die "加载环境后仍未找到 atc"
    [[ "$(python --version 2>&1)" == "Python 3.9.2" ]] || \
        die "ascend-env 的 Python 版本不是 3.9.2"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) MODEL_PATH="${2:-}"; shift 2 ;;
        --input-shape) INPUT_SHAPE="${2:-}"; shift 2 ;;
        --insert-op-conf) INSERT_OP_CONF="${2:-}"; shift 2 ;;
        --output) OUTPUT_PREFIX="${2:-}"; shift 2 ;;
        --soc-version) SOC_VERSION="${2:-}"; shift 2 ;;
        --enable-single-stream) ENABLE_SINGLE_STREAM="${2:-}"; shift 2 ;;
        --enable-small-channel) ENABLE_SMALL_CHANNEL="${2:-}"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) die "未知参数：$1" ;;
    esac
done

set -euo pipefail

[[ -n "${MODEL_PATH}" ]] || die "--model 不能为空"
[[ -n "${INPUT_SHAPE}" ]] || die "--input-shape 不能为空"
[[ -n "${OUTPUT_PREFIX}" ]] || die "--output 不能为空"
[[ -n "${SOC_VERSION}" ]] || die "--soc-version 不能为空"
[[ "${INPUT_SHAPE}" == *:* ]] || die "--input-shape 格式应为 input_name:n,c,h,w"
[[ "${ENABLE_SINGLE_STREAM}" =~ ^(true|false)$ ]] || die "--enable-single-stream 只能是 true 或 false"
[[ "${ENABLE_SMALL_CHANNEL}" =~ ^[01]$ ]] || die "--enable-small-channel 只能是 0 或 1"

MODEL_PATH="$(absolute_path "${MODEL_PATH}")"
INSERT_OP_CONF="$(absolute_path "${INSERT_OP_CONF}")"
OUTPUT_PREFIX="$(absolute_path "${OUTPUT_PREFIX}")"

[[ -f "${MODEL_PATH}" ]] || die "ONNX模型不存在：${MODEL_PATH}"
[[ -f "${INSERT_OP_CONF}" ]] || die "AIPP配置不存在：${INSERT_OP_CONF}"

ATC_COMMAND=(
    atc
    --framework=5
    --model="${MODEL_PATH}"
    --input_shape="${INPUT_SHAPE}"
    --insert_op_conf="${INSERT_OP_CONF}"
    --output="${OUTPUT_PREFIX}"
    --enable_single_stream="${ENABLE_SINGLE_STREAM}"
    --enable_small_channel="${ENABLE_SMALL_CHANNEL}"
    --soc_version="${SOC_VERSION}"
)

printf 'ONNX转海思3403昇腾NNN参数：\n'
printf '  model                : %s\n' "${MODEL_PATH}"
printf '  input_shape          : %s\n' "${INPUT_SHAPE}"
printf '  insert_op_conf       : %s\n' "${INSERT_OP_CONF}"
printf '  output               : %s.om\n' "${OUTPUT_PREFIX}"
printf '  soc_version          : %s\n' "${SOC_VERSION}"
printf '  enable_single_stream : %s\n' "${ENABLE_SINGLE_STREAM}"
printf '  enable_small_channel : %s\n' "${ENABLE_SMALL_CHANNEL}"
printf 'ATC命令：\n  '
printf '%q ' "${ATC_COMMAND[@]}"
printf '\n'

if [[ ${DRY_RUN} -eq 1 ]]; then
    printf 'dry-run完成，未生成OM文件。\n'
    exit 0
fi

load_ascend_env
mkdir -p "$(dirname "${OUTPUT_PREFIX}")"

start_time="$(date +%s)"
"${ATC_COMMAND[@]}"
elapsed="$(( $(date +%s) - start_time ))"
[[ -f "${OUTPUT_PREFIX}.om" ]] || die "ATC返回成功，但未找到输出文件：${OUTPUT_PREFIX}.om"
printf 'ONNX转昇腾NNN OM成功：%s.om\n' "${OUTPUT_PREFIX}"
printf '转换耗时：%s秒\n' "${elapsed}"
