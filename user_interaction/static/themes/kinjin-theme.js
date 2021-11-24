// Modify the DOM
$( document ).ready(function() {
  console.log('hello!')

  html = $('body main').html()
    // Replace X with Y
 
  html = html.replace('Squire', 'スクワイア')
  html = html.replace('squire', 'スクワイア')

  html = html.replace('board games', 'ボードゲーム')
  html = html.replace('boardgames', 'ボードゲーム')
  html = html.replace('Board games', 'ボードゲーム')
  html = html.replace('Boardgames', 'ボードゲーム')
  html = html.replace('board game', 'ボードゲーム')
  html = html.replace('boardgame', 'ボードゲーム')
  html = html.replace('boardgame', 'ボードゲーム') //werkt blijkbaar maar 1 instance, maar vaak tenminste 2x nodig, nog fixen. Daarom 2x dit
  
  html = html.replace('Activities in the next 7 days', '今後7日間の活動')

  html = html.replace('board', 'Student Council')
  html = html.replace('Board', 'Student Council')
  html = html.replace('Boards', 'Student Council')

  html = html.replace('annoying', 'kawaii')
  html = html.replace('troops', 'oniisan')

  html = html.replace('Evil?', 'itai? Doshite! ')
  html = html.replace('Report Bug', 'バグの報告')
  html = html.replace('Hello','こんにちは')
  html = html.replace('Achievements', '実績')
  html = html.replace('Activities', 'アクティビティ')
  html = html.replace('Boardgames', 'ボードゲーム')
  html = html.replace('Roleplaying systems','ロールプレイシステム')
  html = html.replace('Roleplay', 'ロールプレイ')
  html = html.replace('Committees', '委員会')
  html - html.replace('Order','オーダー')
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

  html = html.replace('00:', '24:')
  html = html.replace('01:', '25:')
  html = html.replace('02:', '26:')
  html = html.replace('03:', '27:')
  html = html.replace('04:', '28:')

  html = html.replace('Sign-ups are closed', 'サインアップクローズ')
  html = html.replace('Open for sign-ups', 'サインアップオープン')
  html = html.replace('You are subscribed', 'サブスクライブ')

  html = html.replace('Go to activity', 'アクティビティに移動')
  html = html.replace('Register', '書き記す')
  html - html.replace('Create Slot', 'スロットを作成する')

  $('body main').html(html)
  
  document.getElementById("WelcomeMessage").textContent += "san";
  console.log("san");
  
})


