dir="./data/mcf"
out_dir="./hot_dist/mcf"
prefix="600s"

if [ ! -d $out_dir ];then
    mkdir -p $out_dir
fi

echo "dir: $dir"
echo "out dir: $out_dir"
echo "prefix: $prefix"
echo ""
./hot_distribution -o $out_dir $dir $prefix
