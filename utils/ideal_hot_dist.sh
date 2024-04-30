# 用于给一些调用非常简单的python脚本提供一个通用的调用服务
# 例如：python ./hot_page_life_time.py <benchname>

#benchname_list=(BFS cactuBSSN deepsjeng fotonik3d GUPS mcf PR XZ)
benchname_list=(cactuBSSN deepsjeng fotonik3d GUPS mcf PR XZ)
type_list=('v' 'p')
period_list=(1 5 10)
elf_list=(./bin/ideal_hot_distribution)

for elf_list in "${elf_list[@]}"
do
    for bench in "${benchname_list[@]}"
    do
        for addr_type in "${type_list[@]}"
        do
								echo "${elf_list} --type ${addr_type} --period=1,5,10 ${bench}"
								${elf_list} --type ${addr_type} --period=1,5,10 ${bench}
        done
    done
done

for script in "${script_list[@]}";
do
    for bench in "${benchname_list[@]}";
    do
        echo "python3 ./${script} ${bench}"
        python3 ./${script} ${bench}
    done
done
