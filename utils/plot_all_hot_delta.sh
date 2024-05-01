#benchname_list=(BFS cactuBSSN deepsjeng fotonik3d GUPS mcf PR XZ)
#type_list=('v' 'p')
#period_list=(1 5 10)
benchname_list=(redis)
type_list=('v')
period_list=(1 15 30)

for bench in "${benchname_list[@]}"
do
		for addr_type in "${type_list[@]}"
		do
				for period in "${period_list[@]}"
				do
						python3 ./hot_delta_over_time.py --type ${addr_type} --period ${period} ${bench}
				done
		done
done
