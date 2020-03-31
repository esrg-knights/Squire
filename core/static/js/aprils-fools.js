

timeout = 1000*60*2; // 2 minute timeout


function play_sound() {
    var audio = new Audio('https://interactive-examples.mdn.mozilla.net/media/examples/t-rex-roar.mp3');
    audio.play();
}

setTimeout(play_sound, timeout)
