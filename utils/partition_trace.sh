LINE_PER_SECOND=20000000    # 20,000,000

if [ $# != 3 ]; then
    echo "usage: ./partition_trace.sh <input_dir> <bench_name> <output_dir>"
    exit 1
fi

echo "$LINE_PER_SECOND lines -> 1s"

dir=$1
bench_name=$2
out_dir=$3
input="${dir}/${bench_name}.vout"

if [ ! -f $input ]; then
    echo "File: ${input} does not exists"
    exit 1
fi

if [ ! -d $out_dir ]; then
    mkdir -p $out_dir
fi

# count line number
line_num=$(cat $input | wc -l)
echo "total line num: $line_num"

# split big trace file to some trace file(coresponding to 1s)
# output: bench_n.out
split -d -l${LINE_PER_SECOND} ${input} "${bench_name}_split_middle_"

file_num=0
for file in "${bench_name}"_split_middle_*
do
    cat $file | grep -vi Err | grep -v "=" | grep -v "-" > "${out_dir}/${bench_name}_${file_num}.out"
    rm $file
    echo "$file -> ${out_dir}/${bench_name}_${file_num}.out"
    ((file_num++))
done
echo "num: $file_num"
exit 0

total_err=$(cat $input | grep -i Err | wc -l)
wb_err=$(cat $input | grep -i Err | grep -i "Page Not" | wc -l)
err_ratio=$(echo "scale=6; $total_err * 100 / $line_num" | bc)

echo "wb_err/total_err: ${wb_err}/${total_err}"
echo "total_err ratio: ${err_ratio}%"