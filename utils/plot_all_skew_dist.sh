benchname_list=(liblinear_roi XSBench_64G_roi BC_roi_4thr redis PR_roi_4thr)
type_list=('v')
period_list=(15 30 60 120)
#cacheblock_list=('256' '2M')
threads_num=20

echo "
parallel -j${threads_num} \
	python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/get_skewed_huge_page.py \
	::: --period ::: ${period_list[@]} \
	::: ${benchname[@]} " > log/all_skew_dist.log

parallel -j${threads_num} \
	python3 /home/yangxr/projects/learned_dram/hot_dist/hot_trace/utils/get_skewed_huge_page.py \
	::: --period ::: ${period_list[@]} \
	::: ${benchname_list[@]} 2>&1 >> log/all_skew_dist.log

if [ $? -ne 0 ]
then
	echo "Error! exit"
	exit 1
fi
