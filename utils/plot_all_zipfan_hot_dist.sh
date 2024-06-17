#benchname_list=(BFS cactuBSSN deepsjeng fotonik3d GUPS mcf PR XZ)
#benchname_list=(liblinear_roi BFS500 redis)
#benchname_list=(liblinear_roi XSBench_64G_roi BC_roi_4thr redis XSBench_64G_roi_4thr)
benchname_list=(redis)
type_list=('v')
period_list=(15 30 60 120)
#cacheblock_list=('256' '2M')
cacheblock_list=('2M')
threads_num=4

#for bench in "${benchname_list[@]}"
#do
#		for addr_type in "${type_list[@]}"
#		do
#				for period in "${period_list[@]}"
#				do
#						python3 ./get_zipfan_hot_dist.py --type ${addr_type} --period ${period} ${bench}
#				done
#		done
#done

echo "
for benchname in ${benchname_list[@]}
do
	parallel -j${threads_num} \
		python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/get_zipfan_hot_dist.py \
		--type ::: ${type_list[@]} \
		::: --period ::: ${period_list[@]} \
		::: --cacheblock ::: ${cacheblock_list[@]} \
		::: ${benchname} 2>&1 >> log/all_zipfan_hot_dist.log
done" > log/all_zipfan_hot_dist.log

for benchname in ${benchname_list[@]}
do
	parallel -j${threads_num} \
		python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/get_zipfan_hot_dist.py \
		--type ::: ${type_list[@]} \
		::: --period ::: ${period_list[@]} \
		::: --cacheblock ::: ${cacheblock_list[@]} \
		::: ${benchname} 2>&1 >> log/all_zipfan_hot_dist.log

	if [ $? -ne 0 ]
	then
		echo "${benchname} Error! exit"
		exit 1
	fi
done
