#!/usr/bin/env python

# WS server example

import asyncio
import websockets
import datetime
import random

#!/usr/bin/env python3
import rospy
import signal
#https://github.com/eric-wieser/ros_numpy
import ros_numpy
import sys
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from threading import Thread
import cv2

import base64
global t

# img_str = cv2.imencode('.jpg', img)[1].tostring() / tobyte
# retval, buffer = cv2.imencode('.jpg', image)
# jpg_as_text = base64.b64encode(buffer)

class Test(object):
    def __init__(self):
        self._bridge = CvBridge()
        self._txt_queue = []
        self._img_queue = []
        self._event = asyncio.Event()
        
        self._event_pub = rospy.Publisher("/event2", String, queue_size=1)
        self._event_sub = rospy.Subscriber("/event", String, self.on_event, queue_size = 1)
        #self._img_sub = rospy.Subscriber("/rviz1/camera1/image", Image, self.on_image, queue_size = 1)
        self._img_sub = rospy.Subscriber("/camera/image_raw", Image, self.on_image, queue_size = 1)
        
            
    def on_event(self, msg):
        print(msg)
        self._txt_queue.append(msg.data)
        self._event.set()

    def on_image(self, msg):
        #print("got image")
        cv_image = self._bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
        print(msg.encoding)
        if msg.encoding.startswith("rgb"):
            cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        #img_str = cv2.imencode('.jpg', cv_image)[1].tostring()# / tobyte
        retval, buffer = cv2.imencode('.jpg', cv_image)
        jpg_as_text = base64.b64encode(buffer)

        self._new_img = True
        print(len(self._img_queue))
        if len(self._img_queue)>1:
            self._img_queue.pop()
        self._img_queue.append(jpg_as_text)
        self._event.set()

    async def run(self):
        rospy.spin()

    def signal_handler(self, signal, frame):
        sys.exit()

async def consumer(msg):
    global t
    print(msg)
    t._event_pub.publish(String(msg))

async def producer():
    global t
    while len(t._txt_queue) == 0 and len(t._img_queue) == 0:
        await asyncio.sleep(.001)
    if len(t._txt_queue) > 0:
        return t._txt_queue.pop(0)
    else:
        return t._img_queue.pop(0)



async def consumer_handler(websocket, path):
    async for message in websocket:
        await consumer(message)

async def producer_handler(websocket, path):
    global t
    while(1):
        message = await producer()
        await websocket.send(message)

async def handler(websocket, path):
    consumer_task = asyncio.ensure_future(
        consumer_handler(websocket, path))
    producer_task = asyncio.ensure_future(
        producer_handler(websocket, path))
    done, pending = await asyncio.wait(
        [consumer_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()


rospy.init_node('cloud_filter')
t = Test()
signal.signal(signal.SIGINT, t.signal_handler)
Thread(target=t.run).start()

start_server = websockets.serve(handler, "192.168.0.160", 49154)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()