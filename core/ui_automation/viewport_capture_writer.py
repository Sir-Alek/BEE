import cv2, numpy as np, mss, time, os
import threading

class ScreenRecorder:
    def __init__(self, output_path, monitor=None, fps=20, hwnd=None, max_duration_sec=600):
        self.output_path = output_path
        self.monitor = monitor
        self.hwnd = hwnd
        self.fps = fps
        self.max_duration_sec = max_duration_sec
        self.recording = False
        self.thread = None

    def _current_monitor(self):
        if self.hwnd is not None:
            from core.ui_automation.window_capture import hwnd_to_monitor
            return hwnd_to_monitor(self.hwnd)
        if self.monitor:
            return self.monitor
        return {"top": 0, "left": 0, "width": 1920, "height": 1080}

    def start(self):
        """Inicia la grabación en un thread separado"""
        try:
            # Crear directorio si no existe
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            self.recording = True
            self.thread = threading.Thread(target=self._record, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            print(f"Error iniciando grabación: {e}")
            return False

    def _record(self):
        """Método de grabación en thread separado"""
        try:
            sct = mss.mss()
            fourcc = cv2.VideoWriter_fourcc(*"XVID")
            out = None
            writer_size = None
            frame_count = 0
            started = time.time()

            while self.recording and (time.time() - started) < self.max_duration_sec:
                try:
                    monitor = self._current_monitor()
                    if not monitor:
                        time.sleep(1.0 / self.fps)
                        continue

                    img = np.array(sct.grab(monitor))
                    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    h, w = frame.shape[:2]

                    if out is None or writer_size != (w, h):
                        if out is not None:
                            out.release()
                        writer_size = (w, h)
                        out = cv2.VideoWriter(
                            self.output_path,
                            fourcc,
                            self.fps,
                            writer_size,
                        )

                    if frame.shape[1] != writer_size[0] or frame.shape[0] != writer_size[1]:
                        frame = cv2.resize(frame, writer_size)

                    out.write(frame)
                    frame_count += 1
                    time.sleep(1.0 / self.fps)
                except Exception as e:
                    print(f"Error en frame {frame_count}: {e}")
                    break

            if out is not None:
                out.release()
            print(f"Grabación completada. {frame_count} frames guardados.")
        except Exception as e:
            print(f"Error en grabación de video: {e}")

    def stop(self):
        """Detiene la grabación"""
        self.recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

if __name__ == "__main__":
    pass