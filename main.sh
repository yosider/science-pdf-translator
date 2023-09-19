parent_path="/mnt/g/マイドライブ/Zotero"
# parent_path="/mnt/c/Users/${USER}/Downloads"
output_path="__nougat_output"
nougat "${parent_path}/$1.pdf" -o ${output_path}
python main.py "${output_path}/$1.mmd" "${@:2}"
# rm -rf ${output_path}
