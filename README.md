# Fetch Data Engineering Project

## Overview

This script is a Kafka consumer-producer pipeline that:

* Consumes messages from the user-login Kafka topic.
* Processes data by categorizing users based on IP address, locale, and device type.
* Aggregates processed data every 30 seconds.
* Produces aggregated results to a new Kafka topic called processed_data

## Dependencies
Please ensure you have python 3.11 or later installed. Also, please ensure that you have the confluent-kafka library installed as well.
```
pip install confluent-kafka
```
## Running the Script
1. To start Kafka services, please run the following command in your terminal
    ```
    docker-compose up -d
    ```

2. Run the Consumer-Producer Script
    ```
    python kafka/kafka_script.py
    ```

## Kafka Configuration
### Kafka Broker Connection
```
KAFKA_BROKER = 'localhost:29092'
```
* The Kafka broker is running locally on port 29092.
* This is where the consumer and producer connect to fetch and send messages.

### Kafka Consumer Configuration
```
consumer_conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': 'consumer-login-group-id',
    'auto.offset.reset': 'latest'
}
consumer = Consumer(consumer_conf)
consumer.subscribe(['user-login'])
```
* group.id: Identifies the consumer group.
* auto.offset.reset = 'latest': Only processes new messages arriving after the consumer starts.
* Subscribes to the user-login topic to start consuming messages.

### Kafka Producer Configuration
```
producer_conf = {'bootstrap.servers': KAFKA_BROKER}
producer = Producer(producer_conf)
```
* The producer is configured to connect to localhost:29092.
* It sends processed data to the Kafka topic processed_data.

## Data Processing
### Tracking Login Counts
```
login_counts = defaultdict(int)
interval = 30
processed_data = defaultdict(int)
```
* A defaultdict(int) tracks occurrences of each user group.
* The script processes and aggregates login events every 30 seconds.

### IP Address Categorization
The script extracts the first segment of the IP address (X.Y.Z.W → X). Then, it categorizes the user into a network type:
```
large_network_user_range = [1, 126]
medium_network_user_range = [128, 191]
small_network_user_range = [192, 223]
multicast_user_range = [224, 239]
experimental_user_range = [240, 255]
localhost_range = [127, 127]
```
The classification logic:
```
if ip_address_first_digit_as_int >= large_network_user_range[0] and ip_address_first_digit_as_int <= large_network_user_range[1]:
    processed_data_group_key_ip = 'User from Large Sized Network'
elif ip_address_first_digit_as_int >= medium_network_user_range[0] and ip_address_first_digit_as_int <= medium_network_user_range[1]:
    processed_data_group_key_ip = 'User from Medium Sized Network'
# ... (other conditions follow the same structure)
```
This determines if a user is from a Large, Medium, Small, Multicast, Experimental, or Localhost Network.

### Extracting Additional Attributes
```
if 'locale' in input_data_as_dict:
    processed_data_group_key_locale = input_data_as_dict['locale']
else:
    processed_data_group_key_locale = 'NA'

if 'device_type' in input_data_as_dict:
    processed_data_group_key_device_type = input_data_as_dict['device_type']
else:
    processed_data_group_key_device_type = 'NA'
```
* Extracts locale and device type from the message.
* If missing, assigns 'NA' as a default value.

### Creating a User Grouping Key
```
processed_data_group_key = f'User Group with following Attributes: Location: {processed_data_group_key_locale}, Network Type: {processed_data_group_key_ip}, Device Type: {processed_data_group_key_device_type}'

processed_data[processed_data_group_key] += 1
```
* Groups users based on locale, network type, and device type.
* Counts occurrences of each unique combination.

## Aggregation & Producing to Kafka
Every 30 seconds, the script:

1. Sorts the aggregated data by login count in descending order. The reason this is done is to identify any interesting patterns in the types of users logging into our application (for example, which states/countries they are logging in from, whether they are logging in as part of a large network vs a smaller one, etc).
2. Sends the processed data to Kafka.

```
if time.time() - last_sent_time >= interval:
    processed_data_sorted = dict(sorted(processed_data.items(), key=lambda item: item[1], reverse=True))
    print(processed_data_sorted)
    producer.produce('processed_data', json.dumps(processed_data_sorted).encode('utf-8'))
    producer.flush()
    last_sent_time = time.time()
```
* Sorting: Ensures the most frequent user groups appear first.
* Produces JSON-encoded data to processed_data Kafka topic.
* Flushes the producer to ensure delivery.

### Example of a grouped output by the script: 
```
{''User Group with following Attributes: Location: WI, Network Type: User from Large Sized Network, Device Type: iOS': 8, 'User Group with following Attributes: Location: ME, Network Type: User from Large Sized Network, Device Type: android': 8, 'User Group with following Attributes: Location: MO, Network Type: User from Large Sized Network, Device Type: iOS': 8, 'User Group with following Attributes: Location: MS, Network Type: User from Large Sized Network, Device Type: iOS': 7, 'User Group with following Attributes: Location: UT, Network Type: User from Large Sized Network, Device Type: iOS': 7, 'User Group with following Attributes: Location: MO, Network Type: User from Large Sized Network, Device Type: android': 6, 'User Group with following Attributes: Location: TN, Network Type: User from Large Sized Network, Device Type: android': 6, 'User Group with following Attributes: Location: NC, Network Type: User from Large Sized Network, Device Type: iOS': 6, ... }
```
* Here, for example, we can see that our largest user group is a set of 8 users from Wisconsin who are part of a large network and access our application using an IOS device. We have another group of users from Maine who are also on a large network, but who access our application using Android devices.

If we move further down in the grouped output, we can see we have different types of users. For example, we have one user from Indiana, who is using an experimental network type to access our application.
```
{...User Group with following Attributes: Location: IL, Network Type: User from Experimental Network, Device Type: android': 1,...}
```
* There are many potential use cases for this type of aggregated data. We could see which geographic locations have a lot of traction with our application. We can also see what device types our application is most popular with. We could extend this analysis to other use cases as well. For example, if we have cybersecurity concerns, we could analyze the IP addresses of the users logging in to see if they might be bots, or if they are attempting to mask their identity with a VPN, etc. 

## Exception Handling
The script handles errors gracefully:
```
except KeyboardInterrupt:
    print("Shutting down consumer...")
except Exception as e:
    print(f"The following error occurred: {e}")
finally:
    consumer.close()
```
* KeyboardInterrupt: Allows safe shutdown via Ctrl+C.
* Generic Exception Handling: Catches and logs unexpected errors.
* finally: consumer.close(): Ensures the consumer is properly closed.

## Efficiency & Scalability
### Efficiency
* The script processes incoming messages in real time, ensuring minimal latency.
* Data aggregation occurs every 30 seconds, reducing unnecessary Kafka writes and improving throughput. This also allows the aggregation of a decent amount of data before flushing the producer, allowing us to search for interesting insights in the data. 
* Using defaultdict(int) optimizes memory usage for counting operations.

### Scalability
* Kafka's partitioning mechanism allows multiple consumers in the same consumer group to distribute the load efficiently.
* The script can be deployed on multiple instances, with Kafka handling partition reassignment dynamically.
* Batch processing every 30 seconds ensures that Kafka is not overwhelmed with frequent writes while maintaining near real-time analytics.
* The pipeline can be extended to handle more attributes or integrate with external databases for long-term storage.

## Additional Questions
1. How would you deploy this application in production? - I would deploy this on a cloud service like AWS, using EKS for orchestration. That way, our application can scale in a reliable and cost-effective manner. Depending on how we might want to schedule how this pipeline runs, we could use Apache Airflow as a scheduling service. Alternatively, we can also handle this in AWS using services like AWS Lambda or KEDA. 

    In production, I would deploy the cluster with multiple brokers (at least 3 brokers for fault tolerance). In our current implementation, there is only one Kafka broker, which means that if it goes down for any reason, our application will go completely offline. Similarly, with Zookeeper, I would set up a Zookeeper ensemble (3+ nodes) for high availability. I would have to be sure that the network is configured so that Kafka brokers can communicate with each other and that they are accessible from the clients (producers and consumers). I would also want to set up monitoring and logging for our cluster, using a tool like Datadog. 
    
    Security concerns must also be addressed, which could also be taken care of using AWS build-in IAM authentication and security groups. Regarding modifying settings for producers, I would want to set acks to “all” for strong durability guarantees and use compression to reduce network and storage costs. When it comes to modifying the consumer settings, I would tune the fetch.max.bytes and max.poll.records parameters to optimize the consumer’s throughput and resource usage. 
    
    I would store the code on Github to keep track of versioning, set up a main branch that has the production code, and set up a develop branch that the developers on our team can merge their code into (once they have obtained the proper approvals, of course.) I would create CI/CD jobs in Jenkins and use these to deploy the code in our production environment, which would be hosted on AWS. 

    While there is much more that could be done to optimize production deployment to have a scalable, fault-tolerant application, these are some of the initial steps I would take. 

2. What other components would you want to add to make this production ready? - In addition to what I mentioned previously regarding adding additional Kafka Brokers and Zookeeper Nodes, I would want to be able to store my transformed data in a cloud database, for example perhaps a Cassandra database stored on an EC2 instance.

3. How can this application scale with a growing dataset? - As the dataset grows, we can increase the number of partitions for each topic to scale horizontally. We can also consider our partition strategy, for example perhaps partitioning based on the locale field or the device_type field. We can also scale the Kafka producers with multiple producer instances. Similarly, we can also set up additional consumer instances and group them into consumer groups. We are already batching the data before sending it so this will also help as the dataset grows. As previously mentioned, we can also scale horizontally by adding more Kafka brokers and Zookeeper nodes. 