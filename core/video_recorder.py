import cv2, numpy as np, mss, time, threading, os

class ScreenRecorder:
    def __init__(self, output_path, monitor=None, fps=20):
        self.output_path = output_path
        self.monitor = monitor or {"top": 0, "left": 0, "width": 1920, "height": 1080}
        self.fps = fps
        self.recording = False
        self.thread = None

    def start(self):
        self.recording = True
        self.thread = threading.Thread(target=self._record)
        self.thread.start()

    def _record(self):
        sct = mss.mss()
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        out = cv2.VideoWriter(self.output_path, fourcc, self.fps,
                              (self.monitor["width"], self.monitor["height"]))
        while self.recording:
            img = np.array(sct.grab(self.monitor))
            frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            out.write(frame)
            time.sleep(1 / self.fps)
        out.release()

    def stop(self):
        self.recording = False
        if self.thread:
            self.thread.join()
