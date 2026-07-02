export const API_DATA_FILES_CHANGED = "elia-api-data-files-changed";

export function notifyApiDataFilesChanged(): void {
  window.dispatchEvent(new Event(API_DATA_FILES_CHANGED));
}
