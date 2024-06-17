#benchname_list=(BFS cactuBSSN deepsjeng fotonik3d GUPS mcf PR XZ)
#benchname_list=(liblinear_roi SSSP500 BFS500 redis)
#benchname_list=(SSSP500)
#benchname_list=(redis liblinear_roi XSBench_64G_roi BC_roi_4thr XSBench_64G_roi_4thr)
benchname_list=(redis)
type_list=('v')
period_list=(15 30 60 120)
#cacheblock_list=('256' '2M')
cacheblock_list=('2M')
threads_num=4

echo "
for benchname in ${benchname_list[@]}
do
	parallel -j${threads_num} \
		python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/plot_global_cdf.py \
		--type ::: ${type_list[@]} \
		::: --period ::: ${period_list[@]} \
		::: --cacheblock ::: ${cacheblock_list[@]} \
		::: ${benchname} 2>&1 >> log/all_access_freq.log

	if [ $? -ne 0 ]
	then
		echo "${benchname} Error! exit"
		exit 1
	fi
done" > log/all_access_freq.log

for benchname in ${benchname_list[@]}
do
	parallel -j${threads_num} \
		python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/plot_global_cdf.py \
		--type ::: ${type_list[@]} \
		::: --period ::: ${period_list[@]} \
		::: --cacheblock ::: ${cacheblock_list[@]} \
		::: ${benchname} 2>&1 >> log/all_access_freq.log

	if [ $? -ne 0 ]
	then
		echo "${benchname} Error! exit"
		exit 1
	fi
done
