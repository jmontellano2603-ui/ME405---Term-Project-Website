from pyb import Pin, Timer

class Motor:
    '''A motor driver interface encapsulated in a Python class. Works with
       motor drivers using separate PWM and direction inputs such as the DRV8838
       drivers present on the Romi chassis from Pololu.'''
    
    def __init__(self, PWM, DIR, nSLP):
        '''Initializes a Motor object'''
        self.nSLP_pin = Pin(nSLP, mode=Pin.OUT_PP, value=0)
        ## Right Motor Setup ##
        self.direction= Pin(DIR, Pin.OUT_PP)   ## Control Direction of Right Motor ##
        self.pwm = PWM
  



    
    def set_effort(self, effort):
        '''Sets the present effort requested from the motor based on an input value
           between -100 and 100'''
        if effort < 0:
            #print('Reverse Reverse (two stomps this time)')
            effort = effort * -1
            self.direction.high()
            self.pwm.pulse_width_percent(effort)

        elif effort > 0:
            #print('Forward')
            self.direction.low()
            self.pwm.pulse_width_percent(effort)
        elif effort == 0:
            self.pwm.pulse_width_percent(0)
            print('No effort')
        pass
            
    def enable(self):
        '''Enables the motor driver by taking it out of sleep mode into brake mode'''
        self.nSLP_pin.high()
        print('Enabled')
        pass
            
    def disable(self):
        '''Disables the motor driver by taking it into sleep mode'''
        self.nSLP_pin.low()
        print('Disabled')

        pass
