from gpiozero import LED, MotionSensor
from time import sleep
from signal import pause

# led = LED(4)
# led.off()
# led.on()
# sleep(5)
# led.off()

pir = MotionSensor(17)

def on_motion():
    print("Motion detected!")

def on_no_motion():
    print("No motion detected")

pir.when_motion = on_motion
pir.when_no_motion = on_no_motion

print("Warming up 30s....")
sleep(30)
print("Done")


while True:
    print("MOTION" if pir.motion_detected else "still")
    sleep(0.5)