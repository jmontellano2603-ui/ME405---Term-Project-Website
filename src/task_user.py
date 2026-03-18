''' This file demonstrates an example UI task using a custom class with a
    run method implemented as a generator
'''
from pyb import USB_VCP, UART
from task_share import Share, BaseShare
import micropython



S0_INIT = micropython.const(0) # State 0 - initialiation
S1_CMD  = micropython.const(1) # State 1 - wait for character input
S2_COL  = micropython.const(2) # State 2 - wait for data collection to end
S3_DIS  = micropython.const(3) # State 3 - display the collected data
S4_CHECKPOINT = micropython.const(4) # State 4 - wait for checkpoint run to finish

UI_prompt = ">: "

class task_user:
    '''
    A class that represents a UI task. The task is responsible for reading user
    input over a serial port, parsing the input for single-character commands,
    and then manipulating shared variables to communicate with other tasks based
    on the user commands.
    '''
    def _print(self, msg):
        # msg can be str or bytes
        self._ser.write(msg)
        self._bridge.send_text(msg)   # mirror everything to BT

    def _get_line(self):
        """
        Returns a completed line (str) if available from BT or USB, else None.
        Line is returned WITHOUT CR/LF.
        """

        # 1) Prefer BT line if available (so you can use the BT PuTTY window to control it)
        if self._bridge.bt_line_available():
            b = self._bridge.read_bt_line()
            if b is not None:
                return b.decode("utf-8","ignore").strip()

        # 2) Otherwise, build a USB line buffer until Enter
        while self._ser.any():
            ch = self._ser.read(1)
            if not ch:
                break

            # Handle backspace
            if ch in (b"\x08", b"\x7f"):
                if self._usb_line_buf:
                    self._usb_line_buf = self._usb_line_buf[:-1]
                    self._ser.write(b"\b \b")
                continue

            # Echo what user types (optional)
            self._ser.write(ch)

            if ch in (b"\r", b"\n"):
                line = bytes(self._usb_line_buf).decode("utf-8","ignore").strip()
                self._usb_line_buf = bytearray()
                return line
            else:
                self._usb_line_buf += ch

        return None

    def _get_char(self):
        # 1) Bluetooth raw byte
        if self._bridge.uart.any():
            b = self._bridge.uart.read(1)
            if b:
                return b.decode("utf-8", "ignore")

        # 2) USB byte
        if self._ser.any():
            b = self._ser.read(1)
            if b:
                return b.decode("utf-8", "ignore")

        return None


    def __init__(self, leftMotorGo, rightMotorGo,
             leftdataValues, lefttimeValues, leftvelValues,
             rightdataValues, righttimeValues, rightvelValues,
             ki_value, kp_value, setpoint_value, bridge, line_enable,
             queue_enable, time_disable, obs_go, est_x, est_y,
             est_heading, checkpoint_go):
        
        '''
        Initializes a UI task object
        
        Args:
            leftMotorGo (Share):  A share object representing a boolean flag to
                                  start data collection on the left motor
            rightMotorGo (Share): A share object representing a boolean flag to
                                  start data collection on the right motor
            dataValues (Queue):   A queue object used to store collected encoder
                                  position values
            timeValues (Queue):   A queue object used to store the time stamps
                                  associated with the collected encoder data
        '''
        self._line_enable: Share = line_enable
        self._state: int          = S0_INIT      # The present state
        
        self._leftMotorGo: Share  = leftMotorGo  # The "go" flag to start data
                                                 # collection from the left
                                                 # motor and encoder pair
        
        self._rightMotorGo: Share = rightMotorGo # The "go" flag to start data
                                                 # collection from the right
                                                 # motor and encoder pair
                
        
        self._ser: stream         = USB_VCP()    # A serial port object used to
                                                 # read character entry and to
                                                 # print output
        self._leftdataValues = leftdataValues
        self._lefttimeValues = lefttimeValues
        self._leftvelValues  = leftvelValues
        self._rightdataValues = rightdataValues
        self._righttimeValues = righttimeValues
        self._rightvelValues  = rightvelValues
        self._ki_value: Share = ki_value 
        self._kp_value: Share = kp_value 
        self._setpoint_value: Share = setpoint_value
        self._ser.write("User Task object instantiated\r\n")
        self._bridge = bridge
        self._ser = USB_VCP()
        self._usb_line_buf = bytearray()
        self._queue_enable: Share = queue_enable
        self._time_disable: Share = time_disable
        self._observer_go: Share = obs_go
        self._est_x      = est_x
        self._est_y      = est_y
        self._est_hdg    = est_heading
        self._checkpoint_go = checkpoint_go

        
    def run(self):
            '''
            Runs one iteration of the task
            '''
            self.out_share: BaseShare = Share('f', name="A float share")
            self.char_buf: str      = ""
            self.digits:   set(str) = set(map(str,range(10)))
            self.term:     set(str) = {"\r", "\n"}

            while True:
                
                if self._state == S0_INIT: # Init state (can be removed if unneeded)
                    self._print("+----------------------------------------------+\r\n")
                    self._print("| User Task Initialized                        |\r\n")
                    self._print("+----------------------------------------------+\r\n")
                    self._print("| h | Print help menu                          |\r\n")
                    self._print("| k | Enter New Gain and Setpoint              |\r\n")
                    self._print("| s | Choose a New Setpoint                    |\r\n")
                    self._print("| l | Enable/Disable Line Following            |\r\n")
                    self._print("| q | Enable/Disable Queueing                  |\r\n")
                    self._print("| t | Enable/Disable Timed Run                 |\r\n")
                    self._print("| g | Trigger step response and Print Results  |\r\n")
                    self._print("| r | Run checkpoint course (line follow 90deg)|\r\n")
                    self._print("+----------------------------------------------+\r\n")
                    self._print(UI_prompt)
                    self._state = S1_CMD
        
                elif self._state == S1_CMD: # Wait for UI commands
                    # Wait for at least one character in serial buffer
                    line = None
                    while line is None:
                        line = self._get_line()
                        yield self._state


                    if line:
                        # Read the character and decode it into a string
                        inChar = line[0]
                        # If the character is an upper or lower case "l", start data
                        # collection on the left motor and if it is an "r", start
                        # data collection on the right motor
                        if inChar in {"h", "H"}:
                            #self._ser.write(f"{inChar}\r\n") If you want what the user types to appear in the terminal
                            self._print("https://chatgpt.com/\r\n")
                            self._state = S0_INIT
                        elif inChar in {"k", "K"}:
                            self._print("Enter New Kp Value first, than New Ki\r\n")
                            self._print("Default Values\r\n")
                            self._print("Kp: 0.1\r\n")
                            self._print("Ki: 0.00005\r\n")
                            char_buf = ""
                            done = False
                            while not done:
                                kp_value = self._get_char()
                                if kp_value is not None:
                                    if kp_value in self.digits:
                                        self._ser.write(kp_value)
                                        char_buf += kp_value
                                    elif kp_value == "." and "." not in char_buf:
                                        self._ser.write(kp_value)
                                        char_buf += kp_value
                                    elif kp_value == "\x7f" and len(char_buf) > 0:
                                        self._ser.write(kp_value)
                                        char_buf = char_buf[:-1]
                                    elif kp_value in self.term:
                                        if len(char_buf) == 0:
                                            self._ser.write("\r\n")
                                            self._print("Value not changed\r\n")
                                            char_buf = ""
                                            done = True
                                        elif char_buf not in {"-", "."}:
                                            self._ser.write("\r\n")
                                            value = float(char_buf)
                                            self.out_share.put(value)
                                            char_buf = ""
                                            done = True
                            self._kp_value.put(value)
                            self._print(f"New Kp Value is: {value}\r\n")
                            done = False
                            while not done:
                                ki_value = self._get_char()
                                if ki_value is not None:
                                    if ki_value in self.digits:
                                        self._ser.write(ki_value)
                                        char_buf += ki_value
                                    elif ki_value == "." and "." not in char_buf:
                                        self._ser.write(ki_value)
                                        char_buf += ki_value
                                    elif ki_value == "-" and len(char_buf) == 0:
                                        self._ser.write(ki_value)
                                        char_buf += ki_value
                                    elif ki_value == "\x7f" and len(char_buf) > 0:
                                        self._ser.write(ki_value)
                                        char_buf = char_buf[:-1]
                                    elif ki_value in self.term:
                                        if len(char_buf) == 0:
                                            self._ser.write("\r\n")
                                            self._print("Value not changed\r\n")
                                            char_buf = ""
                                            done = True
                                        elif char_buf not in {"-", "."}:
                                            self._ser.write("\r\n")
                                            value = float(char_buf)
                                            self._ki_value.put(value)
                                            char_buf = ""
                                            done = True
                            self._ki_value.put(value)
                            self._print(f"New Ki Value is: {value}\r\n")
                            self._state = S0_INIT
                        elif inChar in {"s", "S"}:
                            done = False
                            char_in = ""
                            char_buf = ""
                            self._print("The Default Setpoint is 60 mm/s\r\n")
                            self._print("PLease Enter A New Setpoint Value\r\n")
                            while not done:
                                setpoint_value = self._get_char()
                                if setpoint_value is not None:
                                    char_in = setpoint_value
                                    if char_in in self.digits:
                                        self._ser.write(char_in)
                                        char_buf += char_in
                                    elif char_in == "." and "." not in char_buf:
                                        self._ser.write(char_in)
                                        char_buf += char_in
                                    elif char_in == "-" and len(char_buf) == 0:
                                        self._ser.write(char_in)
                                        char_buf += char_in
                                    elif char_in == "\x7f" and len(char_buf) > 0:
                                        self._ser.write(char_in)
                                        char_buf = char_buf[:-1]
                                    elif char_in in self.term:
                                        if len(char_buf) == 0:
                                            self._ser.write("\r\n")
                                            self._print("Value not changed\r\n")
                                            char_buf = ""
                                            done = True
                                        elif char_buf not in {"-", "."}:
                                            self._ser.write("\r\n")
                                            value = float(char_buf)
                                            self._setpoint_value.put(value)
                                            self._print(f"Value set to {value} mm/s\r\n")
                                            char_buf = ""
                                            done = True  
                            self._setpoint_value.put(value) 
                            self._print(f"New setpoint value is now: {value} mm/s \r\n")
                            self._state = S0_INIT
                            
                        elif inChar in {"l", "L"}:
                            done = False
                            self._print("By Defualt Line Following is Enabled\r\n")
                            self._print("Press T to Enable it, or F to Disable it\r\n")
                            while not done:
                                inChar = self._get_char()
                                if inChar in {"t", "T"}:
                                    self._line_enable.put(True)
                                    self._print("Line Following Enabled\r\n")
                                    done = True
                                elif inChar in {"f", "F"}:
                                    self._line_enable.put(False)
                                    self._print("Line Following Disabled\r\n")
                                    done = True
                            self._state = S0_INIT
                        
                        elif inChar in {"q", "Q"}:
                            done = False
                            self._print("By Defualt Queueing is Disabled\r\n")
                            self._print("Press T to Enable it, or F to Disable it\r\n")
                            while not done:
                                inChar = self._get_char()
                                if inChar in {"t", "T"}:
                                    self._queue_enable.put(True)
                                    self._print("Queueing Enabled\r\n")
                                    done = True
                                elif inChar in {"f", "F"}:
                                    self._queue_enable.put(False)
                                    self._print("Queueing Disabled\r\n")
                                    done = True
                            self._state = S0_INIT

                        elif inChar in {"t", "T"}:
                            done = False
                            self._print("By Defualt Timer is Enabled\r\n")
                            self._print("Press T to Enable it, or F to Disable it\r\n")
                            while not done:
                                inChar = self._get_char()
                                if inChar in {"t", "T"}:
                                    self._time_disable.put(True)
                                    self._print("Timer Enabled\r\n")
                                    done = True
                                elif inChar in {"f", "F"}:
                                    self._time_disable.put(False)
                                    self._print("Timer Disabled\r\n")
                                    done = True
                            self._state = S0_INIT

                        elif inChar in {"r", "R"}:
                            self._checkpoint_go.put(True)
                            self._print("Checkpoint run started: line following until 90 deg turn.\r\n")
                            self._print("Waiting for run to complete...\r\n")
                            self._state = S4_CHECKPOINT

                        if inChar in {"g", "G"}:
                            self._print(f'L for left motor, R for right motor, or B for both\r\n')
                            done = False
                            while not done:
                                char_in = self._get_char()
                                if char_in is not None:
                                    if char_in in {"l", "L"}:
                                        self._print("Running step response on left motor\r\n")
                                        self._leftMotorGo.put(True)
                                        done = True
                                    elif char_in in {"r", "R"}:
                                        self._print("Running step response on right motor\r\n")
                                        self._rightMotorGo.put(True)
                                        done = True
                                    elif char_in in {"b", "B"}:
                                        self._print("Running step response on both motors\r\n")
                                        self._leftMotorGo.put(True)
                                        self._rightMotorGo.put(True)
                                        self._line_enable.put(True)
                                        self._observer_go.put(True)
                                        done = True
                                    
                            self._print("Starting motor loop...\r\n")
                            self._print("Starting data collection...\r\n")
                            self._print("Please wait... \r\n")
                            self._state = S2_COL


                elif self._state == S2_COL:
                    # While the data is collecting (in the motor task) block out the
                    # UI and discard any character entry so that commands don't
                    # queue up in the serial buffer
                    if self._ser.any(): self._ser.read(1)
                    # When both go flags are clear, the data collection must have
                    # ended and it is time to print the collected data.
                    if not self._leftMotorGo.get() and not self._rightMotorGo.get():
                        self._line_enable.put(False)
                        self._print("Data collection complete...\r\n")
                        self._print("Printing data...\r\n")
                        self._print("--------------------\r\n")
                        self._print("Time, Position, Velocity\r\n")
                        self._state = S3_DIS
                
                elif self._state == S3_DIS:

                    # --- PRINT LEFT MOTOR DATA FIRST ---
                    if self._leftdataValues.any():
                        line = f"{self._lefttimeValues.get()},{self._leftdataValues.get()},{self._leftvelValues.get()}\r\n"
                        self._print(line)


                    # --- AFTER LEFT IS EMPTY, PRINT RIGHT ---
                    elif self._rightdataValues.any():
                        line = f"{self._righttimeValues.get()},{self._rightdataValues.get()},{self._rightvelValues.get()}\r\n"
                        self._print(line)

                    # --- WHEN BOTH ARE EMPTY ---
                    else:
                        self._print("--------------------\r\n")
                        self._print(f"Estimated X: {self._est_x.get():.2f}\r\n")
                        self._print(f"Estimated Y: {self._est_y.get():.2f}\r\n")
                        self._print(f"Estimated Heading: {self._est_hdg.get():.2f}\r\n")
                        self._print(UI_prompt)
                        self._state = S0_INIT


                elif self._state == S4_CHECKPOINT:
                    # Discard any serial input while the checkpoint run is active
                    if self._ser.any():
                        self._ser.read(1)
                    # checkpoint_task clears checkpoint_go when the run finishes
                    if not self._checkpoint_go.get():
                        self._print("Checkpoint run complete.\r\n")
                        self._state = S0_INIT

                yield self._state


