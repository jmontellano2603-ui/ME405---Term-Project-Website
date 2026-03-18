from time import ticks_us, ticks_diff   # Use to get dt value in update()
from pyb import Pin, Timer

class Encoder:
    '''A quadrature encoder decoding interface encapsulated in a Python class'''

    def __init__(self, tim, chA_pin, chB_pin, name):
        """Initializes an Encoder object.

        `tim` may be either a `pyb.Timer` instance or an integer timer id.
        """
        self.position = 0
        self.prev_count = 0
        self.delta = 0
        self.dt = 500
        self.start = ticks_us()
        # Accept either a Timer instance or a timer id
        if isinstance(tim, Timer):
            self.timer = tim
        else:
            self.timer = Timer(int(tim), period=0xFFFF, prescaler=0)

        self.Enc_A = Pin(chA_pin)
        self.Enc_B = Pin(chB_pin)
        # store pin identifiers and optional name for labeled prints
        self.chA_pin = chA_pin
        self.chB_pin = chB_pin
        self.name = name
        self.timer.channel(1, pin=self.Enc_A, mode=Timer.ENC_AB)
        self.timer.channel(2, pin=self.Enc_B, mode=Timer.ENC_AB)
        self.timer.counter(0)


    def update(self):
        '''Runs one update step on the encoder's timer counter to keep
           track of the change in count and check for counter reload'''
        if ticks_diff(ticks_us(), self.start) >= 500:
            self.dt = ticks_diff(ticks_us(), self.start)
            current = self.timer.counter()
            label = f'[{self.name}]' if self.name else f'[{self.chA_pin}/{self.chB_pin}]'
            if abs(current - self.prev_count) > 32768:
                if current - self.prev_count > 32768:
                    self.position = self.position - 1
                    #print(label, 'Reversed', current)
                elif current - self.prev_count < 32768:
                    self.position = self.position + 1
                    #print(label, 'Forward', current)
            #print(label, 'Position:', current)
            self.delta = current - self.prev_count
            self.prev_count = current
            self.start = ticks_us()
    
            
    def get_position(self):
        '''Returns the most recently updated value of position as determined
           within the update() method'''
        return self.position * 65536 + self.timer.counter()
            
    def get_velocity(self):
        '''Returns a measure of velocity using the the most recently updated
           value of delta as determined within the update() method'''
        #print("Delta:", self.delta, "dt:", self.dt)
        return (self.delta*0.153)/(self.dt/(10**6))
    
    def zero(self):
        '''Sets the present encoder position to zero and causes future updates
           to measure with respect to the new zero position'''
        self.timer.counter(0) 
        self.position   = 0
        self.prev_count = 0
        self.delta      = 0
        self.start      = ticks_us()
        pass