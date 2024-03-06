inputDir=./hot_dist/mcf 
outputDir=./plot/mcf

filePrefix_list=('20s' '300s' '600s')

if [ ! -d $outputDir ];then
		mkdir -p $outputDir
fi

for prefix in ${filePrefix_list[@]};
do
		echo "python plot_static_dist.py -p $prefix -d $inputDir -o $outputDir"
		time python plot_static_dist.py -p $prefix -d $inputDir -o $outputDir
done
