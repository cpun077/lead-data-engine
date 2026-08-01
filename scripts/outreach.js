const SHEET_ID = '1RIyon84yA7ArN0miI-O0dnKQmAQbblbnrH6_-nrHa_Q'
const INDUSTRY = 'consulting'
const RANKING = 'Tier 1 and Tier 2'

const SUBJECT = `Survey of your peers`;
const SURVEY_PAGE = 'overbase.app/survey'
const FORMS = {
  'gov':'app.youform.com/forms/fzbwyu0j',
  'accounting':'app.youform.com/forms/yndcsdzi',
  'consulting':'app.youform.com/forms/ag4g8wda',
  'business insurance':'app.youform.com/forms/cmjzeg1v',
  'law':'app.youform.com/forms/ufpjpl7c',
}


// Initial Email
const FIRST_BODY = firstName => `Hi ${firstName},

Overbase is starting our annual survey of ${RANKING} marketers.

Every year we find the most innovative ${INDUSTRY} firm CMOs based on this survey.

Do you have 1 minute to anonymously answer 2 questions?
${FORMS[INDUSTRY]}`;
const HTML_FIRST_BODY = firstName =>
  FIRST_BODY(firstName)
    .replace(
      `survey of ${RANKING} marketers`,
      `<a href="http://${SURVEY_PAGE}">survey of ${RANKING} marketers</a>`
    )
    .replace(
      FORMS[INDUSTRY],
      `<a href="https://${FORMS[INDUSTRY]}">${FORMS[INDUSTRY]}</a>`
    )
    .replace(/\n/g, '<br>');

function firstDraft() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Sheet1');
  const rows = sheet.getDataRange().getValues();
  for (let i = 1; i < /*rows.length*/25; i++) {
    const [company, name, title, email, status, threadID] = rows[i];
    if ((status && status.startsWith('drafted')) || !email) continue;
    const firstName = String(name).trim().split(/\s+/)[0];
    
    const draft = GmailApp.createDraft(email, SUBJECT, FIRST_BODY(firstName), {
      htmlBody: HTML_FIRST_BODY(firstName),
    });
    sheet.getRange(i + 1, 5).setValue('drafted_1');
    sheet.getRange(i + 1, 6).setValue(draft.getMessage().getThread().getId());
  }
}

// First Followup
const SECOND_BODY = firstName => `Overbase is a Silicon Valley startup backed by Reid Hoffman, founder of LinkedIn.

+1,200 marketers answered our survey last year.

Anonymously answer in 1 minute
${FORMS[INDUSTRY]}

Or read about the survey here.`;
const HTML_SECOND_BODY = firstName =>
  SECOND_BODY(firstName)
    .replace(
      'Reid Hoffman, founder of LinkedIn.',
      '<a href="https://en.wikipedia.org/wiki/Reid_Hoffman">Reid Hoffman, founder of LinkedIn.</a>'
    )
    .replace(
      FORMS[INDUSTRY],
      `<a href="https://${FORMS[INDUSTRY]}">${FORMS[INDUSTRY]}</a>`
    )
    .replace(
      'here.',
      `<a href="http://${SURVEY_PAGE}">here.</a>`
    )
    .replace(/\n/g, '<br>');

function secondDraft() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Sheet1');
  const rows = sheet.getDataRange().getValues();
  for (let i = 1; i < /*rows.length*/25; i++) {
    const [company, name, title, email, status, threadID] = rows[i];
    if (status !== 'drafted_1' || !email) continue;
    const firstName = String(name).trim().split(/\s+/)[0];

    // const threads = GmailApp.search(`in:sent to:${email} subject:"${SUBJECT}"`);
    // if (threads.length === 0) continue;
    // const thread = threads[0];
    if (!threadID) continue;
    const thread = GmailApp.getThreadById(threadID);
    if (!thread) continue;

    thread.createDraftReply(SECOND_BODY(firstName), {
      htmlBody: HTML_SECOND_BODY(firstName),
    });
    sheet.getRange(i + 1, 5).setValue('drafted_2');
    sheet.getRange(i + 1, 6).setValue(thread.getId());
  }
}

// Second Followup
const THIRD_BODY = firstName => `Only marketers at ${RANKING} firms are surveyed.

And we determine who the most innovative CMOs are entirely based on survey responses.

It takes 1 minute to anonymously answer
${FORMS[INDUSTRY]}`;
const HTML_THIRD_BODY = firstName =>
  THIRD_BODY(firstName)
    .replace(
      FORMS[INDUSTRY],
      `<a href="https://${FORMS[INDUSTRY]}">${FORMS[INDUSTRY]}</a>`
    )
    .replace(/\n/g, '<br>');

function thirdDraft() {
  const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName('Sheet1');
  const rows = sheet.getDataRange().getValues();
  for (let i = 1; i < /*rows.length*/25; i++) {
    const [company, name, title, email, status, threadID] = rows[i];
    if (status !== 'drafted_2' || !email) continue;
    const firstName = String(name).trim().split(/\s+/)[0];

    if (!threadID) continue;
    const thread = GmailApp.getThreadById(threadID);
    if (!thread) continue;
    
    thread.createDraftReply(THIRD_BODY(firstName), {
      htmlBody: HTML_THIRD_BODY(firstName),
    });
    sheet.getRange(i + 1, 5).setValue('drafted_3');
  }
}