import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Tailwind sınıflarını koşullu birleştirir + çakışmaları çözer (shadcn/ui standardı). */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
