"use client";

let audioElement: HTMLAudioElement | null = null;

export function registerAudioElement(element: HTMLAudioElement | null): void {
  audioElement = element;
}

export function seekTo(seconds: number): void {
  if (audioElement) {
    audioElement.currentTime = seconds;
  }
}

export function getAudioElement(): HTMLAudioElement | null {
  return audioElement;
}
