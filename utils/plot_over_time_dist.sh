inputDir=./hot_dist/PR
outputDir=./plot/PR

filePrefix_list=('BFS')
beginFileIdx_list=(0 11 21 31 41 51)
fileNum_list=(10 20 30 40 50 56)
targetFreq_list=(5 15)

if [ ! -d $outputDir ];then
		mkdir -p $outputDir
fi

for (( n=0 ; n<${#beginFileIdx_list[@]} ; n++));
do
		echo "python plot_range_dist.py -p ${filePrefix_list[$n]} \
			-d $inputDir -o $outputDir \
			-b ${beginFileIdx_list[$n]} -n ${fileNum_list[$n]} \
			-f ${targetFreq_list[@]}"
		 time python3 plot_range_dist.py -p ${filePrefix_list[0]} -d $inputDir -o $outputDir \
		 	-b ${beginFileIdx_list[$n]} -n ${fileNum_list[$n]} -f ${targetFreq_list[@]}
done
