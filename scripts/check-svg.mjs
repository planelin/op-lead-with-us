import { readFileSync } from 'node:fs';

const svg = readFileSync('assets/mascot.svg', 'utf8');

// Check for /* or */ anywhere in the file
console.log('Contains /*:', svg.includes('/*'));
console.log('Contains */:', svg.includes('*/'));

// Check for unclosed tags or syntax
let lines = svg.split('\n');
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('/*') || lines[i].includes('*/')) {
    console.log(`Line ${i + 1}: ${lines[i].trim()}`);
  }
}
