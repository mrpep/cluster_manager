import subprocess
from termcolor import colored
import time

def _get_disk_info(host):
    cmd = 'df -h'
    ssh_command = 'ssh {} {}'.format(host, cmd)
    result = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)
    disk_data = [{'device': l.split()[0], 
                    'size': l.split()[1], 
                    'used': l.split()[2], 
                    'available': l.split()[3],
                    'use': l.split()[4],
                    'mntpoint': l.split()[5] } for l in result.stdout.split('\n')[1:] if l != '']
    return disk_data

def _get_gpu_info(host):
    cmd = "nvidia-smi --query-gpu=name,memory.free,memory.used,memory.total,utilization.gpu,temperature.gpu --format=csv,noheader,nounits"
    ssh_command = 'ssh {} {}'.format(host, cmd)
    result = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)
    gpu_str = result.stdout
    gpu_data = [{'name': l.split(',')[0],
                'mem_free': l.split(',')[1],
                'mem_used': l.split(',')[2],
                'mem_total': l.split(',')[3],
                'gpu_use': l.split(',')[4],
                'gpu_temp': l.split(',')[5]} for l in gpu_str.split('\n') if l != '']
    return gpu_data

def _get_ram_info(host):
    cmd = 'free -h'
    ssh_command = 'ssh {} {}'.format(host, cmd)
    result = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)
    mem_data = {}
    mem = result.stdout.split('\n')[1]
    mem_data['total'] = mem.split()[1]
    mem_data['used'] = mem.split()[2]
    mem_data['available'] = mem.split()[-1]
    swap = result.stdout.split('\n')[2]
    mem_data['swap'] = swap.split()[1]
    mem_data['swap_free'] = swap.split()[3]
    return mem_data

def _get_cpu_info(host):
    cmd = 'cat /proc/stat'
    ssh_command = 'ssh {} {}'.format(host, cmd)
    result1 = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)
    time.sleep(1)
    result2 = subprocess.run(ssh_command, shell=True, check=True, capture_output=True, text=True)
    cores1 = [[int(li) for li in l.split()[1:]] for l in result1.stdout.split('\n') if l.startswith('cpu') and len(l.split()[0])>3]
    cores2 = [[int(li) for li in l.split()[1:]] for l in result2.stdout.split('\n') if l.startswith('cpu') and len(l.split()[0])>3]
    cpu_time_on = [sum(c2) - sum(c1) for c1, c2 in zip(cores1, cores2)]
    cpu_time_idle = [(c2[3] + c2[4]) - (c1[3] + c1[4]) for c1, c2 in zip(cores1, cores2)]
    cpu_usage = [100*(s-i)/s for s,i in zip(cpu_time_on, cpu_time_idle)]
    return cpu_usage

def print_resources(servers):
    for server in servers:
        print('🖥 Resource information for {}'.format(colored(server, 'blue')))
        limits = [25,75]
        try:
            cpu_data = _get_cpu_info(server)
            print('   🔲CPUs:')
            print('      Threads: {}'.format(len(cpu_data)))
            cpu_usage_str = '         '
            for i,c in enumerate(cpu_data):
                if (i+1)%16 == 0:
                    cpu_usage_str += '\n         '
                if c < limits[0]:
                    color = 'green'
                elif c < limits[1]:
                    color = 'blue'
                else:
                    color = 'red'
                cpu_usage_str += colored('{:>4d}'.format(int(c)), color)
            print(cpu_usage_str)
        except:
            print('   🥺Unable to retrieve CPU information.')

        try:
            mem_data = _get_ram_info(server)
            print('   🚀Memory use: {}/{}'.format(mem_data['used'], mem_data['total']))
        except:
            print('   🥺Unable to retrieve memory use information.')
        try:
            gpu_data = _get_gpu_info(server)
            print('   🔲GPUs:')
            for gpu in gpu_data:
                print('      {:<30}:\t{}/{} Temp: {}°C Usage: {}%'.format(colored(gpu['name'][:30],'blue'),
                                                                gpu['mem_used'],
                                                                gpu['mem_total'],
                                                                gpu['gpu_temp'],
                                                                gpu['gpu_use']))
        except:
            print('   🥺No GPU Found or Driver Failed.')
        try:
            disk_data = _get_disk_info(server)
            #Filter relevant disks:
            relevant_disk_data = [d for d in disk_data if d['device'].startswith('/dev') and not d['device'].startswith('/dev/loop')]
            print('   💾Disks:')
            for d in relevant_disk_data:
                print('      {:<10}->{:<15}\tFree space: {}/{}'.format(d['device'].split('/')[-1][:10], d['mntpoint'][:15], d['available'], d['size']))
        except:
            print('   🥺Drive info could not be retrieved.')

        cpu_data = _get_cpu_info(server)