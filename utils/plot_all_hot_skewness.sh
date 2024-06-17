benchname_list=(liblinear_roi XSBench_64G_roi BC_roi_4thr redis PR_roi_4thr)
type_list=('v')
period_list=(15 30 60 120)
#cacheblock_list=('256' '2M')
threads_num=8

for benchname in ${benchname_list[@]}
do
	echo "
	parallel -j${threads_num} \
		python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/plot_hot_skew.py \
		::: --period ::: ${period_list[@]} \
		::: ${benchname} " > log/all_hot_skewness.log

	parallel -j${threads_num} \
		python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/plot_hot_skew.py \
		::: --period ::: ${period_list[@]} \
		::: ${benchname} 2>&1 >> log/all_hot_skewness.log

	if [ $? -ne 0 ]
	then
		echo "${benchname} Error! exit"
		exit 1
	fi
done
