// Modify the DOM
$( document ).ready(function() {
    console.log('hello!')
    html = $('body main').html()
    // Replace 'k' and 'c' by 'q' (leave html between < and > alone)
 
  html = html.replace('board games', 'ボードゲーム')
  html = html.replace('boardgames', 'ボードゲーム')
  html = html.replace('Board games', 'ボードゲーム')
  html = html.replace('Boardgames', 'ボードゲーム')
   html = html.replace('board game', 'ボードゲーム')
   html = html.replace('boardgame', 'ボードゲーム')
  html = html.replace('Activities in the next 7 days', '今後7日間の活動')

  html = html.replace('board', 'Student Council')
  html = html.replace('Board', 'Student Council')

  html = html.replace('annoying', 'kawaii')
  html = html.replace('troops', 'oniisan')

  html = html.replace('Evil?', 'itai? Doshite! ')
  html = html.replace('Report Bug', 'バグの報告')
  html = html.replace('Hello','こんにちは')
  html = html.replace('Achievements', '実績')
  html = html.replace('Activities', '活動')
  html = html.replace('Boardgames', 'ボードゲーム')
  html = html.replace('Roleplay', 'ロールプレイ')
  html = html.replace('Committees', '委員会')
  html = html.replace('Account', 'アカウント')

  html = html.replace('Monday', 'げつようび')
  html = html.replace('Tuesday', 'かようび')
  html = html.replace('Wednesday', 'すいようび')
  html = html.replace('Thursday', 'もくようび')
  html = html.replace('Friday', 'きんようび')
  html = html.replace('Saturday', 'どようび')
  html = html.replace('Sunday', 'にちようび')

  html = html.replace('Januari', '一月')
  html = html.replace('Februari', '二月')
  html = html.replace('March', '三月')
  html = html.replace('April', '四月')
  html = html.replace('May', '五月')
  html = html.replace('June', '	六月')
  html = html.replace('July', '七月')
  html = html.replace('August', '八月')
  html = html.replace('September', '九月')
  html = html.replace('October', '十月')
  html = html.replace('November', '十一月')
  html = html.replace('December', '十二月')

  html = html.replace('Sign-ups are closed', 'サインアップは締め切られました')
  html = html.replace('Open for sign-ups', 'サインアップのために開いています')
  html = html.replace('You are subscribed', 'あなたは購読しています')

  html = html.replace('Go to activity', 'アクティビティに移動')
  html = html.replace('Register', '書き記す')
  html - html.replace('Create Slot', 'スロットを作成する')
  html = html.replace('Registrations are required! You cannot join this activity otherwise!', '登録が必要です！それ以外の場合は、このアクティビティに参加できません。')

    $('body main').html(html)
})
// function googleTranslateElementInit() {
//   new google.translate.TranslateElement({pageLanguage: 'en', layout: google.translate.TranslateElement.InlineLayout.SIMPLE}, 'google_translate_element');
// }


// <script type="text/javascript" src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit"></script>