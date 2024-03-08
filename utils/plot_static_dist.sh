inputDir=./hot_dist/PR
outputDir=./plot/PR

#filePrefix_list=('20s' '300s' '600s')
filePrefix_list=('pr_300s')
fileIndex=0
targetFreq_list=(5 15 25)

if [ ! -d $outputDir ];then
		mkdir -p $outputDir
fi

for prefix in ${filePrefix_list[@]};
do
		echo "python plot_static_dist.py -p $prefix -d $inputDir -o $outputDir -i ${fileIndex} -f ${targetFreq_list[@]}"
		time python plot_static_dist.py -p $prefix -d $inputDir -o $outputDir -i ${fileIndex} -f ${targetFreq_list[@]}
done
