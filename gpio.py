from gpiozero import LED, TonalBuzzer

def turn_on_led(pin_number):
    led = LED(pin_number)
    led.on()

def turn_of_led(pin_number):
    led = LED(pin_number)
    led.off()

def play_buzzer_sound(pin_number, sound):
    buzzer = TonalBuzzer(pin_number)
