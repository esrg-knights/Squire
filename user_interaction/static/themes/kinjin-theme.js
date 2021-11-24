// Modify the DOM
$(document).ready(function () {
    console.log('hello!')

    html = $('body main').html()
    // Replace X with Y

    html = html.replaceAll('Squire', 'スクワイア')
    html = html.replaceAll('squire', 'スクワイア')

    html = html.replaceAll('board games', 'ボードゲーム')
    html = html.replaceAll('boardgames', 'ボードゲーム')
    html = html.replaceAll('Board games', 'ボードゲーム')
    html = html.replaceAll('Boardgames', 'ボードゲーム')
    html = html.replaceAll('board game', 'ボードゲーム')
    html = html.replaceAll('boardgame', 'ボードゲーム')

    html = html.replaceAll('Activities in the next 7 days', '今後7日間の活動')

    html = html.replaceAll('board', 'Student Council')
    html = html.replaceAll('Board', 'Student Council')
    html = html.replaceAll('Boards', 'Student Council')

    html = html.replaceAll('annoying', 'kawaii')
    html = html.replaceAll('troops', 'oniisan')

    html = html.replaceAll('Evil?', 'itai? Doshite! ')
    html = html.replaceAll('Report Bug', 'バグの報告')
    html = html.replaceAll('Hello', 'こんにちは')
    html = html.replaceAll('Achievements', '実績')
    html = html.replaceAll('Activities', 'アクティビティ')
    html = html.replaceAll('Boardgames', 'ボードゲーム')
    html = html.replaceAll('Roleplaying systems', 'ロールプレイシステム')
    html = html.replaceAll('Roleplay', 'ロールプレイ')
    html = html.replaceAll('Committees', '委員会')
    html - html.replaceAll('Order', 'オーダー')
    html = html.replaceAll('Account', 'アカウント')

    html = html.replaceAll('Monday', 'げつようび')
    html = html.replaceAll('Tuesday', 'かようび')
    html = html.replaceAll('Wednesday', 'すいようび')
    html = html.replaceAll('Thursday', 'もくようび')
    html = html.replaceAll('Friday', 'きんようび')
    html = html.replaceAll('Saturday', 'どようび')
    html = html.replaceAll('Sunday', 'にちようび')

    html = html.replaceAll('Januari', '一月')
    html = html.replaceAll('Februari', '二月')
    html = html.replaceAll('March', '三月')
    html = html.replaceAll('April', '四月')
    html = html.replaceAll('May', '五月')
    html = html.replaceAll('June', '	六月')
    html = html.replaceAll('July', '七月')
    html = html.replaceAll('August', '八月')
    html = html.replaceAll('September', '九月')
    html = html.replaceAll('October', '十月')
    html = html.replaceAll('November', '十一月')
    html = html.replaceAll('December', '十二月')

    html = html.replaceAll('00:', '24:')
    html = html.replaceAll('01:', '25:')
    html = html.replaceAll('02:', '26:')
    html = html.replaceAll('03:', '27:')
    html = html.replaceAll('04:', '28:')

    html = html.replaceAll('Sign-ups are closed', 'サインアップクローズ')
    html = html.replaceAll('Open for sign-ups', 'サインアップオープン')
    html = html.replaceAll('You are subscribed', 'サブスクライブ')

    html = html.replaceAll('Go to activity', 'アクティビティに移動')
    html = html.replaceAll('Register', '書き記す')
    html - html.replaceAll('Create Slot', 'スロットを作成する')

    $('body main').html(html)

    document.getElementById("WelcomeMessage").textContent += "san";
    console.log("san");

})


