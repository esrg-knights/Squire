"use strict";

/** A better replace text function
 *
 * @param {Node} element
 * @param {RegExp|string} pattern
 * @param {string} replacement
 *
 * @copyright https://stackoverflow.com/a/50537862/4633439
 */
function replaceInText(element, pattern, replacement) {
    for (let node of Array.from(element.childNodes)) {
        switch (node.nodeType) {
            case Node.ELEMENT_NODE:
                replaceInText(node, pattern, replacement);
                break;
            case Node.TEXT_NODE:
                node.textContent = node.textContent.replace(pattern, replacement);
                break;
            case Node.DOCUMENT_NODE:
                replaceInText(node, pattern, replacement);
        }
    }
}

// Modify the DOM
$(document).ready(function () {
    console.debug('hello!')

    const textReplaceFn = replaceInText.bind(null, document.body);

    // Replace X with Y

    textReplaceFn('Squire', 'スクワイア')
    textReplaceFn('squire', 'スクワイア')

    textReplaceFn(/board\s*games?/muig, 'ボードゲーム');
    textReplaceFn(/Sword\s*fighting/muig, '侍');

    textReplaceFn('Activities in the next 7 days', '今後7日間の活動')

    textReplaceFn('board', 'Student Council')
    textReplaceFn('Board', 'Student Council')
    textReplaceFn('Boards', 'Student Council')

    textReplaceFn('annoying', 'kawaii')
    textReplaceFn('troops', 'oniisan')

    textReplaceFn('Evil?', 'バグ? Doshite! ')
    textReplaceFn('Report Bug', 'バグの報告')
    textReplaceFn('Hello', 'こんにちは')
    textReplaceFn('Achievements', '実績')
    textReplaceFn('Activities', 'アクティビティ')
    textReplaceFn('Boardgames', 'ボードゲーム')
    textReplaceFn('Roleplaying systems', 'ロールプレイシステム')
    textReplaceFn('roleplaying systems', 'ロールプレイシステム')    
    textReplaceFn('Roleplay', 'ロールプレイ')
    textReplaceFn('roleplay', 'ロールプレイ')
    textReplaceFn('Committees', '委員会')
    textReplaceFn('Orders', 'オーダー')
    textReplaceFn('Order', 'オーダー')
    textReplaceFn('Account', 'アカウント')
    textReplaceFn('Association', 'アソシエーション')
    textReplaceFn('association', 'アソシエーション')


    textReplaceFn('Membership', 'メンバーシップ')
    textReplaceFn('membership', 'メンバーシップ')

    textReplaceFn('Address', 'アドレス')
    textReplaceFn('address', 'アドレス')

    textReplaceFn('Contact', 'コンタクト')
    textReplaceFn('contact', 'コンタクト')

    textReplaceFn('Calendar', 'カレンダー')
    textReplaceFn('calendar', 'カレンダー')

    textReplaceFn('Monday', 'げつようび')
    textReplaceFn('Tuesday', 'かようび')
    textReplaceFn('Wednesday', 'すいようび')
    textReplaceFn('Thursday', 'もくようび')
    textReplaceFn('Friday', 'きんようび')
    textReplaceFn('Saturday', 'どようび')
    textReplaceFn('Sunday', 'にちようび')

    textReplaceFn('Januari', '一月')
    textReplaceFn('Februari', '二月')
    textReplaceFn('March', '三月')
    textReplaceFn('April', '四月')
    textReplaceFn('May', '五月')
    textReplaceFn('June', '	六月')
    textReplaceFn('July', '七月')
    textReplaceFn('August', '八月')
    textReplaceFn('September', '九月')
    textReplaceFn('October', '十月')
    textReplaceFn('November', '十一月')
    textReplaceFn('December', '十二月')

    textReplaceFn('00:', '24:')
    textReplaceFn('01:', '25:')
    textReplaceFn('02:', '26:')
    textReplaceFn('03:', '27:')
    textReplaceFn('04:', '28:')

    textReplaceFn('Sign-ups are closed', 'サインアップクローズ')
    textReplaceFn('Open for sign-ups', 'サインアップオープン')
    textReplaceFn('You are subscribed', 'サブスクライブ')

    textReplaceFn('Go to activity', 'アクティビティに移動')
    textReplaceFn('Register', '書き記す')
    textReplaceFn('Create Slot', 'スロットを作成する')


    let html = $('body main').html();

    html = html.replaceAll(/background-image:\s*url\([A-z\/\\0-9.:]*swords\.png\);/gmui, "background-image: url(./images/kinjin/soa.png);")
    html = html.replaceAll(/background-image:\s*url\([A-z\/\\0-9.:]*external-content\.duckduckgo\.com\.jpg\);/gmui, "background-image: url(./images/kinjin/kfc.png);") //christmas=kfc
    html = html.replaceAll(/background-image:\s*url\([A-z\/\\0-9.:]*bgs\.png\);/gmui, "background-image: url(./images/kinjin/no-game-no-life.png);")

    //This might break some javascript
    $('body main').html(html);

    if (document.getElementById("WelcomeMessage")) //Saw no better way to do it.
        document.getElementById("WelcomeMessage").textContent += "san";
    console.debug("san");

})
