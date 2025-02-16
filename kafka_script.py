from confluent_kafka import Consumer, Producer, KafkaException
from collections import defaultdict
import json
import time

KAFKA_BROKER = 'localhost:29092'

consumer_conf = {
    'bootstrap.servers': KAFKA_BROKER,
    'group.id': 'consumer-login-group-id',
    'auto.offset.reset': 'latest'
}

producer_conf = {'bootstrap.servers': KAFKA_BROKER}
consumer = Consumer(consumer_conf)
producer = Producer(producer_conf)
consumer.subscribe(['user-login'])

login_counts = defaultdict(int)
interval = 30
large_network_user_range = [1, 126]
medium_network_user_range = [128, 191]
small_network_user_range = [192, 223]
multicast_user_range = [224, 239]
experimental_user_range = [240, 255]
localhost_range = [127, 127]

try:
    last_sent_time = time.time()
    processed_data = defaultdict(int)
    while True:
        msg = consumer.poll()

        if msg is None:
            continue
        if msg.error():
            raise KafkaException(msg.error())

        user_event = msg.value().decode('utf-8')
        print(f"Received message: {user_event}")

        input_data_as_dict = json.loads(user_event)

        if 'ip' in input_data_as_dict:
            ip_address_split = input_data_as_dict['ip'].split('.')
            ip_address_first_digit = ip_address_split[0]
            ip_address_first_digit_as_int = int(ip_address_first_digit)

            if ip_address_first_digit_as_int >=  large_network_user_range[0] and ip_address_first_digit_as_int <= large_network_user_range[1]:
                processed_data_group_key_ip = 'User from Large Sized Network'
            elif ip_address_first_digit_as_int >=  medium_network_user_range[0] and ip_address_first_digit_as_int <= medium_network_user_range[1]:
                processed_data_group_key_ip = 'User from Medium Sized Network'
            elif ip_address_first_digit_as_int >=  small_network_user_range[0] and ip_address_first_digit_as_int <= small_network_user_range[1]:
                processed_data_group_key_ip = 'User from Small Sized Network'
            elif ip_address_first_digit_as_int >=  multicast_user_range[0] and ip_address_first_digit_as_int <= multicast_user_range[1]:
                processed_data_group_key_ip = 'User from Multicast Network'
            elif ip_address_first_digit_as_int >=  experimental_user_range[0] and ip_address_first_digit_as_int <= experimental_user_range[1]:
                processed_data_group_key_ip = 'User from Experimental Network'
            elif ip_address_first_digit_as_int >=  localhost_range[0] and ip_address_first_digit_as_int <= localhost_range[1]:
                processed_data_group_key_ip = 'User from LocalHost Network'
            else:
                processed_data_group_key_ip = 'User from Unkown Network Type'

        if 'locale' in input_data_as_dict:
            processed_data_group_key_locale = input_data_as_dict['locale']
        else:
            processed_data_group_key_locale = 'NA'

        if 'device_type' in input_data_as_dict:
            processed_data_group_key_device_type = input_data_as_dict['device_type']
        else:
            processed_data_group_key_device_type = 'NA'

        processed_data_group_key = f'User Group with following Attributes: Location: {processed_data_group_key_locale}, Network Type: {processed_data_group_key_ip}, Device Type: {processed_data_group_key_device_type}'
        processed_data[processed_data_group_key] += 1

        if time.time() - last_sent_time >= interval:
            processed_data_sorted = dict(sorted(processed_data.items(), key=lambda item: item[1], reverse=True))
            print(processed_data_sorted)
            producer.produce('processed_data', json.dumps(processed_data_sorted).encode('utf-8'))
            producer.flush()
            last_sent_time = time.time()


except KeyboardInterrupt:
    print("Shutting down consumer...")
except Exception as e:
    print(f"The following error occurred: {e}")
finally:
    consumer.close()

