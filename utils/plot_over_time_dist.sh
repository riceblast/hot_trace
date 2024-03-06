inputDir=./hot_dist/mcf 
outputDir=./plot/mcf

filePrefix_list=('20s' '300s' '600s')
#filePrefix_list=('20s')
fileNum_list=(4 4 4)
targetFreq_list=(5 15 25)

if [ ! -d $outputDir ];then
		mkdir -p $outputDir
fi

for (( n=0 ; n<${#filePrefix_list[@]} ; n++));
do
		echo "python plot_range_dist.py -p ${filePrefix_list[$n]} \
			-d $inputDir -o $outputDir -n ${fileNum_list[$n]} -f ${targetFreq_list[@]}"
		time python plot_range_dist.py -p ${filePrefix_list[$n]} -d $inputDir -o $outputDir \
			-n ${fileNum_list[$n]} -f ${targetFreq_list[@]}
done
