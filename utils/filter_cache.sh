#!/bin/bash

# 定义输入文件夹路径
input_dir="/home/yangxr/projects/learned_dram/hot_dist/hot_trace/trace/mcf.in"

# 定义输出文件夹
out_dir="./data/mcf"
if [ ! -d $out_dir ];then
		mkdir -p $out_dir
fi

# 定义程序路径（如果filter_cache在PATH中，直接使用filter_cache即可）
filter_cache="./filter_cache"

prefix="600s"
paral_degree=22
echo "path: $input_dir"
echo "out_dir: $out_dir" 
echo "prefix: $prefix"
echo "paral_degree: $paral_degree"

# 使用find命令查找所有的xxx_n.raw.file文件
# 使用parallel命令并行运行filter_cache程序处理这些文件，并在每个文件处理完毕后打印一条消息
# -j16 指定同时运行16个作业
# 使用{}占位符传递文件名给filter_cache，然后使用echo打印每个文件处理完成的消息
# 使用\;来转义分号，以便将其包含在命令字符串中
find "$input_dir" -name "${prefix}*.raw.trace" | parallel -j ${paral_degree} "${filter_cache} -o ${out_dir} {} ; echo {} 已处理完"

echo "所有文件处理完成！"

