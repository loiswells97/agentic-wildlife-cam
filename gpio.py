from gpiozero import LED, RGBLED, TonalBuzzer
from time import sleep

def turn_on_led(pin_number):
    led = LED(pin_number)
    led.on()
    if led.is_lit:
        return True
    return False

def turn_off_led(pin_number):
    led = LED(pin_number)
    led.off()
    if not led.is_lit:
        return True
    return False

def blink_led(pin_number, on_time, off_time, n):
    led = LED(pin_number)
    led.blink(on_time, off_time, n, background=True)
    return True

def play_rgb_led_pattern(red_pin_number, green_pin_number, blue_pin_number, pattern):
    rgb_led = RGBLED(red_pin_number, green_pin_number, blue_pin_number)
    for colour, duration in pattern:
        rgb_led.color = colour
        sleep(duration)
    rgb_led.off()
    return True

def play_buzzer_tune(pin_number, tune):
    buzzer = TonalBuzzer(pin_number)
    # Define your tune: (Note, Duration in seconds)
    # Tune should be in the format of a list of tuples, each tuple containing a note and a duration e.g.
    # tune = [
    #     ('C4', 0.5), ('C4', 0.5), ('G4', 0.5), ('G4', 0.5),
    #     ('A4', 0.5), ('A4', 0.5), ('G4', 1.0)
    # ]

    # Play the tune
    for note, duration in tune:
        buzzer.play(note)
        sleep(duration)
        buzzer.stop()    # Pause briefly between notes
        sleep(0.1)

    # Turn off completely when finished
    buzzer.stop()
    return True
# play_buzzer_tune(27, [('C4', 0.5), ('C4', 0.5), ('G4', 0.5), ('G4', 0.5), ('A4', 0.5), ('A4', 0.5), ('G4', 1.0)])

# blink_led(4, 1,1,5)

# play_rgb_led_pattern(26,19,13,[({'red': 1, 'green': 0,'blue': 0},1)])
