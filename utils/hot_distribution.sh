dir="/home/yangxr/projects/learned_dram/hot_dist/hot_trace/trace/mcf.in"
prefix="300s"

echo "dir: $dir"
echo "prefix: $prefix"
echo ""
./hot_distribution $dir $prefix
