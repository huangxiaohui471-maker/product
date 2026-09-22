#!/bin/zsh
cd -- "${0:A:h}"
if ! command -v python3 >/dev/null 2>&1; then
  echo '请把这个文件夹交给WorkBuddy，让它检查Python环境并打开工作台。'
  read -r
  exit 1
fi
python3 '启动底版.py'
