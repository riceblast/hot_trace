if [ $# -lt 1 ];then
    echo "usage: ./plot_all_CDF.sh <benchname> [v/p]"
    exit 1
fi

trace_dir="/home/yangxr/downloads/test_trace/hot_dist_5_15/${1}"
suffix="hot_v_5_15.out"
virtual=1
if [ -n "${2}" ];then
    if [ "${2}" == 'p' ];then
        suffix="hot_5_15.out"
        virtual=0
    fi
fi

if [ ! -d $trace_dir ];then
    echo "trace dir: ${trace_dir} not exist"
    exit 1
fi

fileCnt=$(ls ${trace_dir} | grep "${suffix}" | wc -l)
echo "Total ${benchname}_*.${suffix} file: ${fileCnt}"

for ((i=0; i<$fileCnt; i++))
do
    if [ $virtual -eq 1 ];then
        python3 ./plot_hot_cdf.py --type v ${1} $i
    else
        python3 ./plot_hot_cdf.py --type p ${1} $i
    fi
done