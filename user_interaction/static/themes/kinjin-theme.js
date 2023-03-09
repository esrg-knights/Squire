"use strict";

const currentDirectoryThemes = "/static/themes/";

// Modify the DOM
$(document).ready(function () {
    console.debug('こんにちは！')

    try {
        performance.mark("金人初め")
    } catch (e) {
        console.warn(e);
    }

    //Array.from(document.getElementsByClassName("knights-logo-img")).forEach((e) => e.src = "/static/themes/images/kinjin/KinjinSpoof.png");

    const textReplaceFn = replaceInText.bind(null, document.body);

    // Replace X with Y

    textReplaceFn('Squire', 'スクワイア')
    textReplaceFn('squire', 'スクワイア')

    textReplaceFn(/board\s*games?/muig, 'ボードゲーム');
    textReplaceFn(/Evening/muig, '夕');
    textReplaceFn(/Sword(\s|-)*fight(ing)?s?/muig, '侍');
    textReplaceFn(/training/muig, '訓練');

    textReplaceFn('Activities in the next 7 days', '今後7日間の活動')

    textReplaceFn(/boards?/muig, 'Student Council')

    textReplaceFn('annoying', 'kawaii')
    textReplaceFn('troops', 'oniisan')

    textReplaceFn('Evil?', 'バグ? Doshite! ')
    textReplaceFn('Report Bug', 'バグの報告')
    textReplaceFn('Hello', 'こんにちは')
    textReplaceFn('Achievements', '実績')
    textReplaceFn('Activities', 'アクティビティ')
    textReplaceFn('Roleplaying systems', 'ロールプレイシステム')
    textReplaceFn(/Roleplay(-?ing)?/muig, 'ロールプレイ')
    textReplaceFn('Committees', '委員会')
    textReplaceFn('Committee', '委員会')
    textReplaceFn(/newsletters?/muig, 'ニューズレター')
    textReplaceFn('roleplaying systems', 'ロールプレイシステム')
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

    textReplaceFn(/Luna/mug, 'ルーナー');
    textReplaceFn(/living\s+room/muig, '居間');
    textReplaceFn('Calendar', 'カレンダー')
    textReplaceFn('calendar', 'カレンダー')

    // week En
    textReplaceFn('Monday', 'げつようび')
    textReplaceFn('Tuesday', 'かようび')
    textReplaceFn('Wednesday', 'すいようび')
    textReplaceFn('Thursday', 'もくようび')
    textReplaceFn('Friday', 'きんようび')
    textReplaceFn('Saturday', 'どようび')
    textReplaceFn('Sunday', 'にちようび')

    // Week NL
    textReplaceFn(/Maandag/muig, 'げつようび')
    textReplaceFn(/Dinsdag/muig, 'かようび')
    textReplaceFn(/Woensdag/muig, 'すいようび')
    textReplaceFn(/Donderdag/muig, 'もくようび')
    textReplaceFn(/Vrijdag/muig, 'きんようび')
    textReplaceFn(/Zaterdag/muig, 'どようび')
    textReplaceFn(/Zondag/muig, 'にちようび')

    //Maand EN
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

    //Maand NL
    textReplaceFn('januari', '一月')
    textReplaceFn('februari', '二月')
    textReplaceFn('maart', '三月')
    textReplaceFn('april', '四月')
    textReplaceFn('mei', '五月')
    textReplaceFn('juni', '	六月')
    textReplaceFn('juli', '七月')
    textReplaceFn('augustus', '八月')
    textReplaceFn('september', '九月')
    textReplaceFn('oktober', '十月')
    textReplaceFn('november', '十一月')
    textReplaceFn('december', '十二月')

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


    const cardImgs = Array.from(document.querySelectorAll(".card-img-top"))

    for (const element of cardImgs) {
        let styleString = element.attributes.style.textContent;

        styleString = styleString.replaceAll(/background-image:\s*url\([A-z\/\\0-9.:]*swords\.png\);/gmui, "background-image: url(/static/themes/images/kinjin/soa.jpg);");
        styleString = styleString.replaceAll(/background-image:\s*url\([A-z\/\\0-9.:]*external-content\.duckduckgo\.com\.jpg\);/gmui, "background-image: url(/static/themes/images/kinjin/kfc.jpg);"); //christmas=kfc
        styleString = styleString.replaceAll(/background-image:\s*url\([A-z\/\\0-9.:]*bgs\.png\);/gmui, "background-image: url(/static/themes/images/kinjin/no-game-no-life.jpg);");
        styleString = styleString.replaceAll(/background-image:\s*url\([A-z\/\\0-9.:]*header_logo\.png\);/gmui, "background-image: url(/static/themes/images/kinjin/KinjinSpoof.png);");

        element.style = styleString;
    }



    if (document.getElementById("WelcomeMessage")) //Saw no better way to do it.
        document.getElementById("WelcomeMessage").textContent += "san";
    console.debug("san");

    try {
        performance.mark("金人終わり")
        performance.measure("金人", "金人初め", "金人終わり")
    } catch (e) {
        console.warn(e);
    }
})

{
    Array.from(document.head.querySelectorAll("link[rel*=icon]")).forEach((e) => e.outerHTML = "");
    const faviconDirectory = currentDirectoryThemes + "/images/kinjin/";
    const faviconLocationPNG = faviconDirectory + "KinjinSpoof-favicon.png"
    //const faviconLocationICO = faviconDirectory + "KinjinSpoof-favicon.ico"
    //const appleIconLocation = faviconDirectory + "apple-touch-icon.png";
    const favicon = document.createElement("link");
    favicon.rel = "icon";
    favicon.href = faviconLocationPNG;

    /*
    const favicon32 = document.createElement("link");
    favicon32.href = faviconDirectory + "favicon-32x32.png";
    favicon32.sizes = "32x32";
    favicon32.rel = "icon";

    const favicon16 = document.createElement("link");
    favicon16.href = faviconDirectory + "favicon-16x16.png";
    favicon16.sizes = "16x16";
    favicon16.rel = "icon";
    */

    const appleIcon = document.createElement("link");
    appleIcon.rel = "apple-touch-icon";
    //appleIcon.sizes = "180x180";
    appleIcon.href = faviconLocationPNG;

    [favicon, appleIcon].forEach((e) => document.head.appendChild(e));
}
