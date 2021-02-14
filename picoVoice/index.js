const Porcupine = require("@picovoice/porcupine-node");
const { COMPUTER } = require("@picovoice/porcupine-node/builtin_keywords");
const recorder = require("node-record-lpcm16");
const process = require('process'); 
const porcupineInstance = new Porcupine([COMPUTER], [0.5]);

const frameLength = porcupineInstance.frameLength;
const sampleRate = porcupineInstance.sampleRate;

console.log("parent process id is " + process.ppid);

const recording = recorder.record({
  sampleRate: sampleRate,
  channels: 1,
  audioType: "raw",
  recorder: "sox",
});

let frameAccumulator = [];

function chunkArray(array, size) {
  return Array.from({ length: Math.ceil(array.length / size) }, (v, index) =>
    array.slice(index * size, index * size + size)
  );
}

recording.stream().on("data", (data) => {
  // Two bytes per Int16 from the data buffer
  let newFrames16 = new Array(data.length / 2);
  for (let i = 0; i < data.length; i += 2) {
    newFrames16[i / 2] = data.readInt16LE(i);
  }
  // Split the incoming PCM integer data into arrays of size Porcupine.frameLength. If there's insufficient frames, or a remainder,
  // store it in 'frameAccumulator' for the next iteration, so that we don't miss any audio data
  frameAccumulator = frameAccumulator.concat(newFrames16);
  let frames = chunkArray(frameAccumulator, frameLength);

  if (frames[frames.length - 1].length !== frameLength) {
    // store remainder from divisions of frameLength
    frameAccumulator = frames.pop();
  } else {
    frameAccumulator = [];
  }

  for (const frame of frames) {
    let index = porcupineInstance.process(frame);
    if (index !== -1) {
      console.log(`Detected 'COMPUTER'`);
      process.kill(process.ppid, 'SIGUSR1')
    }
  }
});

console.log(`Listening for 'COMPUTER'...`);
process.stdin.resume();
console.log("Press ctrl+c to exit.");
