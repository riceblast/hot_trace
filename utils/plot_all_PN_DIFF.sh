#benchname_list=(BFS cactuBSSN deepsjeng fotonik3d GUPS mcf PR XZ)
#type_list=('v' 'p')
#period_list=(1 5 10)
benchname_list=(BC PR redis)
type_list=('v')
period_list=(1 5 15 30)

for bench in "${benchname_list[@]}"
do
		for addr_type in "${type_list[@]}"
		do
				for period in "${period_list[@]}"
				do
						python3 ./plot_pa_difference.py --type ${addr_type} --period ${period} ${bench}
				done
		done
done
