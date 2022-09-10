#!/usr/bin/env python

from base64 import encode
from operator import truediv
from lab_poll_pos import quaternion_to_yaw
import rospy
import socket
import threading
import time

from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from tf.transformations import euler_from_quaternion
from struct import *

HOST = '127.0.0.1'
PORT = 65432

class ROSMonitor:
    def __init__(self):
        # Add your subscriber here (odom? laserscan?):

        self.sub_laser = rospy.Subscriber("/scan", LaserScan, self.scan_laser)
        self.sub_odom = rospy.Subscriber("/odometry/filtered", Odometry, self.scan_odom)
        # Current robot state:
        self.id = 0xFFFF
        self.pos = 0
        self.obstacle = pack("Ixxx",0)

        # Params :
        self.remote_request_port = rospy.get_param("remote_request_port", 65432)
        self.pos_broadcast_port  = rospy.get_param("pos_broadcast_port", 65431)

        # Thread for RemoteRequest handling:
        self.rr_thread = threading.Thread(target=self.rr_loop)
        self.rr_thread.daemon = True
        self.rr_thread.start()

        # check time at the begenning for non-blocking 1Hz
        self.startTime_pb = time.time()

        # Create socket UDP for positionBroadcast
        self.pb_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)       # socket UDP
        self.pb_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)    # Broadcast mode
        self.pb_socket.settimeout(0.2)

        print("ROSMonitor started.")

    def rr_loop(self):
        # Init your socket here :
        # self.rr_socket = socket.Socket(...)
        self.rr_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rr_socket.bind((HOST, PORT))
            self.rr_socket.listen(2)
        except:
            print("erreur while bind or listen")

        (conn,addr) = self.rr_socket.accept()
        while True:
            data = conn.recv(1024)

            if not data:
                break
            elif data.decode("uint_8") == "RPOS":
                conn.send(self.pos)
            elif data.decode("uint_8") == "OBSF":
                conn.send(self.obstacle)
            elif data.decode("uint_8") == "RBID":
                conn.send(pack("Ixxx",self.id))
        conn.close() 
            
    def quaternion_to_yaw(quat):
    # Uses TF transforms to convert a quaternion to a rotation angle around Z.
    # Usage with an Odometry message: 
    #   yaw = quaternion_to_yaw(msg.pose.pose.orientation)
        (roll, pitch, yaw) = euler_from_quaternion([quat.x, quat.y, quat.z, quat.w])
        return yaw

    def scan_laser(self,msg):
        # print(msg.ranges)
        rangesValues = msg.ranges
        for data in rangesValues:
            if data < 1:
                # print("Data",data)
                self.obstacle = pack("Ixxx",1)

        
        # pass

    def scan_odom(self,msg):
        # print('X: ',msg.pose.pose.position.x)
        # print('Y: ',msg.pose.pose.position.y)
        # print('Theta: ',quaternion_to_yaw(msg.pose.pose.orientation))
        self.pos = pack("fffx",msg.pose.pose.position.x,msg.pose.pose.position.y,quaternion_to_yaw(msg.pose.pose.orientation))
        positionTemp = pack("fffI",msg.pose.pose.position.x,msg.pose.pose.position.y,quaternion_to_yaw(msg.pose.pose.orientation),self.id)
        # check if 1 second is elapsed and send data.
        if (time.time() - self.startTime_pb >= 1):
            self.pb_socket.sendto(positionTemp, ('<broadcast>', self.pos_broadcast_port))
            # print("message sent!", time.time())
            self.startTime_pb = time.time()
        

if __name__=="__main__":
    rospy.init_node("ros_monitor")

    node = ROSMonitor()

    rospy.spin()


