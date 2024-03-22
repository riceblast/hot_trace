benchname_list=(BFS cactuBSSN fotonik3d GUPS PR XZ)
type_list=('v' 'p')

for ((bench=0; bench<${#benchname_list[@]}; bench++))
do
    for ((t=0; t<${#type_list[@]}; t++))
    do  
        # plot CDF
        echo "./plot_all_CDF.sh ${benchname_list[$bench]} ${type_list[$t]}"
        ./plot_all_CDF.sh ${benchname_list[$bench]} ${type_list[$t]} 2&>1 >/dev/null

        # plot page number different
        echo "./plot_all_PN_DIFF.sh ${benchname_list[$bench]} ${type_list[$t]}"
        ./plot_all_PN_DIFF.sh ${benchname_list[$bench]} ${type_list[$t]} 2&>1 >/dev/null
    done
done