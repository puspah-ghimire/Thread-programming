import threading
import queue
import random
import time
import matplotlib.pyplot as plt

# Constants
NUM_TELLERS = 3
MAX_QUEUE_SIZE = 5
TIME_QUANTUM = 2

# Data structures
customer_queue = queue.Queue(MAX_QUEUE_SIZE)
customer_pqueue = queue.PriorityQueue(MAX_QUEUE_SIZE)
tellers = []
service_times = {}
remaining_service_times = {}
arrival_times = {}
start_service_times = {}
completion_times = {}
lock = threading.Lock()
stop_arrival = threading.Event()
stop_simulation = threading.Event()
teller_service_data = {1: [], 2: [], 3: []}  # To store service times for each teller
customers_served_by_teller = {1: [], 2: [], 3: []}  # To store customers each teller served
queue_sizes = []  # To store queue sizes over time

# Statistics
total_waiting_time = 0
total_turnaround_time = 0
total_response_time = 0
total_customers = 0

def random_service_time():
    return random.randint(5, 10)

def random_arrival_time():
    return random.randint(0, 2)

def simulate_customer_arrival(queue_type):
    global total_customers
    customer_id = 1
    while not stop_arrival.is_set():
        if not queue_type.full():
            arrival_time = time.time()
            service_time = random_service_time()
            if queue_type == customer_queue:
                queue_type.put(customer_id)
            else:
                queue_type.put((service_time, customer_id))
            service_times[customer_id] = service_time
            remaining_service_times[customer_id] = service_time  
            arrival_times[customer_id] = arrival_time
            print(f"Customer{customer_id} enters the Queue.")
            total_customers += 1
            with lock:
                queue_sizes.append((time.time() - start_time, queue_type.qsize()))
            customer_id += 1
        else:
            print("Queue is FULL.")
        time.sleep(random_arrival_time())

def calculate_and_print_stats(customer_id):
    completion_time = completion_times[customer_id]
    arrival_time = arrival_times[customer_id]
    service_time = service_times[customer_id]
    start_service_time = start_service_times[customer_id]

    turnaround_time = completion_time - arrival_time
    response_time = start_service_time - arrival_time
    waiting_time = turnaround_time - service_time

    global total_waiting_time, total_turnaround_time, total_response_time
    total_waiting_time += waiting_time
    total_turnaround_time += turnaround_time
    total_response_time += response_time

    print(f"Customer{customer_id} - Response Time: {response_time:.2f}s, "
          f"Waiting Time: {waiting_time:.2f}s, Service Time: {service_time:.2f}s, Turnaround Time: {turnaround_time:.2f}s")

def simulate_teller_fcfs(teller_id):
    while not stop_simulation.is_set() or not customer_queue.empty():
        if not customer_queue.empty():
            with lock:
                customer_id = customer_queue.get()
                queue_sizes.append((time.time() - start_time, customer_queue.qsize()))
            start_service_time = time.time()
            start_service_times[customer_id] = start_service_time
            service_time = service_times[customer_id]
            print(f"Customer{customer_id} is in Teller{teller_id}")
            teller_service_data[teller_id].append((customer_id, start_service_time, start_service_time + service_time))
            customers_served_by_teller[teller_id].append(customer_id)
            time.sleep(service_time)
            completion_time = time.time()
            completion_times[customer_id] = completion_time
            print(f"Customer{customer_id} leaves Teller{teller_id}")
            calculate_and_print_stats(customer_id)
        else:
            time.sleep(0.5)

def simulate_teller_sjf(teller_id):
    while not stop_simulation.is_set() or not customer_pqueue.empty():
        if not customer_pqueue.empty():
            with lock:
                min_service_time, customer_id = customer_pqueue.get()
                queue_sizes.append((time.time() - start_time, customer_pqueue.qsize()))
            start_service_time = time.time()
            start_service_times[customer_id] = start_service_time
            print(f"Customer{customer_id} is in Teller{teller_id}")
            teller_service_data[teller_id].append((customer_id, start_service_time, start_service_time + min_service_time))
            customers_served_by_teller[teller_id].append(customer_id)
            time.sleep(min_service_time)
            completion_time = time.time()
            completion_times[customer_id] = completion_time
            print(f"Customer{customer_id} leaves Teller{teller_id}")
            calculate_and_print_stats(customer_id)
        else:
            time.sleep(0.5)

def simulate_teller_psjf(teller_id):
    while not stop_simulation.is_set() or not customer_pqueue.empty():
        if not customer_pqueue.empty():
            with lock:
                min_service_time, customer_id = customer_pqueue.get()
                queue_sizes.append((time.time() - start_time, customer_pqueue.qsize()))
            if customer_id not in start_service_times:
                start_service_times[customer_id] = time.time()
            service_time = service_times[customer_id]
            print(f"Customer{customer_id} is in Teller{teller_id} with {service_time} remaining service time")
            customers_served_by_teller[teller_id].append(customer_id)
            while service_time > 0:
                time.sleep(1)
                service_time -= 1
                teller_service_data[teller_id].append((customer_id, time.time(), time.time() + 1))
                if not customer_pqueue.empty():
                    with lock:
                        next_service_time, next_customer_id = customer_pqueue.queue[0]
                        if next_service_time < service_time:
                            service_times[customer_id] = service_time
                            customer_pqueue.put((service_time, customer_id))
                            print(f"Customer{customer_id} preempted by Customer{next_customer_id}")
                            break
            if service_time <= 0:
                completion_time = time.time()
                completion_times[customer_id] = completion_time
                print(f"Customer{customer_id} leaves Teller{teller_id}")
                calculate_and_print_stats(customer_id)
        else:
            time.sleep(0.5)

def simulate_teller_rr(teller_id):
    while not stop_simulation.is_set() or not customer_queue.empty():
        if not customer_queue.empty():
            with lock:
                customer_id = customer_queue.get()
                queue_sizes.append((time.time() - start_time, customer_queue.qsize()))
            if customer_id not in start_service_times:
                start_service_times[customer_id] = time.time()
            remaining_time = remaining_service_times[customer_id]
            if remaining_time > TIME_QUANTUM:
                remaining_service_times[customer_id] -= TIME_QUANTUM
                print(f"Customer{customer_id} is in Teller{teller_id} for {TIME_QUANTUM} seconds")
                teller_service_data[teller_id].append((customer_id, time.time(), time.time() + TIME_QUANTUM))
                customers_served_by_teller[teller_id].append(customer_id)
                time.sleep(TIME_QUANTUM)
                with lock:
                    customer_queue.put(customer_id)
                print(f"Customer{customer_id} re-enters the Queue")
            else:
                print(f"Customer{customer_id} is in Teller{teller_id} for {remaining_time} seconds")
                teller_service_data[teller_id].append((customer_id, time.time(), time.time() + remaining_time))
                time.sleep(remaining_time)
                completion_time = time.time()
                completion_times[customer_id] = completion_time
                print(f"Customer{customer_id} leaves Teller{teller_id}")
                calculate_and_print_stats(customer_id)
        else:
            time.sleep(0.5)

def stop_simulation_on_keypress():
    input("Press Enter to stop customer arrivals...")
    stop_arrival.set()

def plot_teller_service_data():
    colors = ['r', 'g', 'b']
    labels = ['Teller 1', 'Teller 2', 'Teller 3']
    plt.figure(figsize=(12, 6))

    for teller_id, (color, label) in zip(teller_service_data.keys(), zip(colors, labels)):
        label_once = True
        for service in teller_service_data[teller_id]:
            customer_id, start_time, end_time = service
            plt.plot([start_time, end_time], [teller_id, teller_id], color=color, marker='o', label=label if label_once else "")
            label_once = False
            mid_time = (start_time + end_time) / 2
            plt.text(mid_time, teller_id, f"C{customer_id}", ha='center', va='bottom')

    plt.xlabel('Time (s)')
    plt.ylabel('Teller ID')
    plt.title('Teller Service Times')
    plt.yticks([1, 2, 3], ['Teller 1', 'Teller 2', 'Teller 3'])
    plt.ylim(0.5, 3.5)
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_queue_sizes():
    times, sizes = zip(*queue_sizes)
    plt.figure(figsize=(12, 6))
    plt.plot(times, sizes, marker='o', linestyle='-', color='b')
    plt.xlabel('Time (s)')
    plt.ylabel('Queue Size')
    plt.title('Queue Size Over Time')
    plt.grid(True)
    plt.show()

def main():
    global start_time
    algorithm = input("Enter the scheduling algorithm (fcfs, sjf, psjf, rr): ").strip().lower()
    start_time = time.time()

    if algorithm in ['fcfs', 'rr']:
        arrival_thread = threading.Thread(target=simulate_customer_arrival, args=(customer_queue,))
    else:
        arrival_thread = threading.Thread(target=simulate_customer_arrival, args=(customer_pqueue,))
    arrival_thread.start()

    if algorithm == 'fcfs':
        teller_function = simulate_teller_fcfs
    elif algorithm == 'sjf':
        teller_function = simulate_teller_sjf
    elif algorithm == 'psjf':
        teller_function = simulate_teller_psjf
    elif algorithm == 'rr':
        teller_function = simulate_teller_rr
    else:
        print("Invalid algorithm. Please choose 'fcfs', 'sjf', 'psjf', or 'rr'.")
        stop_arrival.set()
        arrival_thread.join()
        return

    for teller_id in range(NUM_TELLERS):
        teller_thread = threading.Thread(target=teller_function, args=(teller_id + 1,))
        tellers.append(teller_thread)
        teller_thread.start()

    stop_thread = threading.Thread(target=stop_simulation_on_keypress)
    stop_thread.start()

    stop_thread.join()
    arrival_thread.join()

    stop_simulation.set()
    for teller_thread in tellers:
        teller_thread.join()

    if total_customers > 0:
        average_response_time = total_response_time / total_customers
        average_turnaround_time = total_turnaround_time / total_customers
        average_waiting_time = total_waiting_time / total_customers

        print(f"\nAverage Response Time: {average_response_time:.2f}s")
        print(f"Average Turnaround Time: {average_turnaround_time:.2f}s")
        print(f"Average Waiting Time: {average_waiting_time:.2f}s")

    plot_teller_service_data()
    plot_queue_sizes()

if __name__ == "__main__":
    main()