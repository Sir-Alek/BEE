import cv2, numpy as np, mss, time, os
import threading

class ScreenRecorder:
    def __init__(self, output_path, monitor=None, fps=20):
        self.output_path = output_path
        self.monitor = monitor or {"top": 0, "left": 0, "width": 1920, "height": 1080}
        self.fps = fps
        self.recording = False
        self.thread = None

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
            
            out = cv2.VideoWriter(
                self.output_path,
                fourcc,
                self.fps,
                (self.monitor["width"], self.monitor["height"])
            )
            
            frame_count = 0
            max_frames = 3600  # Máximo 1 minuto a 60fps
            
            while self.recording and frame_count < max_frames:
                try:
                    img = np.array(sct.grab(self.monitor))
                    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    out.write(frame)
                    frame_count += 1
                    time.sleep(1.0 / self.fps)
                except Exception as e:
                    print(f"Error en frame {frame_count}: {e}")
                    break
                    
            out.release()
            print(f"Grabación completada. {frame_count} frames guardados.")
        except Exception as e:
            print(f"Error en grabación de video: {e}")

    def stop(self):
        """Detiene la grabación"""
        self.recording = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

if __name__ == "__main__":
    pass