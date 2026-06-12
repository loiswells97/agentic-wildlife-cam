from gpiozero import LED, TonalBuzzer
from time import sleep

def turn_on_led(pin_number):
    led = LED(pin_number)
    led.on()

def turn_of_led(pin_number):
    led = LED(pin_number)
    led.off()

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

# play_buzzer_tune(27, [('C4', 0.5), ('C4', 0.5), ('G4', 0.5), ('G4', 0.5), ('A4', 0.5), ('A4', 0.5), ('G4', 1.0)])