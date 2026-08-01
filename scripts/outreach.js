const SHEET_ID = '1RIyon84yA7ArN0miI-O0dnKQmAQbblbnrH6_-nrHa_Q'
const SUBJECT = `Survey of your peers`;
const SURVEY_PAGE = 'overbase.app/survey'
const INDUSTRIES = {
  'gov':{'form':'app.youform.com/forms/fzbwyu0j', 'ranking':'Top 50 lobbying revenue', 'name':'government relations'},
  'acc':{'form':'app.youform.com/forms/yndcsdzi', 'ranking':'Accounting Today Top 100', 'name':'accounting'},
  't1':{'form':'app.youform.com/forms/ag4g8wda', 'ranking':'Tier 1 and Tier 2', 'name':'consulting'},
  't2':{'form':'app.youform.com/forms/ag4g8wda', 'ranking':'Tier 1 and Tier 2', 'name':'consulting'},
  'insur':{'form':'app.youform.com/forms/cmjzeg1v', 'ranking':'Business Insurance Top 100', 'name':'business insurance'},
  'law':{'form':'app.youform.com/forms/ufpjpl7c', 'ranking':'AmLaw 100', 'name':'law'},
}

// CONFIGURATIONS HERE
const SHEET_NAME = 't2' // Choose sheet to draft emails for
const config = INDUSTRIES[SHEET_NAME]
const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(`${SHEET_NAME}`);
const rows = sheet.getDataRange().getValues();

const START_IDX = 1 // Choose sheet row to start
const END_IDX = rows.length-1 // Choose sheet row to end

// Initial Email
const FIRST_BODY = firstName => `Hi ${firstName},

Overbase is starting our annual survey of ${config['ranking']} marketers.

Every year, we find the most innovative ${config['name']} firm CMOs based on this survey.

Do you have 1 minute to anonymously answer 2 questions?
${config['form']}`;
const HTML_FIRST_BODY = firstName =>
  FIRST_BODY(firstName)
    .replace(
      `survey of ${config['ranking']} marketers`,
      `<a href="http://${SURVEY_PAGE}">survey of ${config['ranking']} marketers</a>`
    )
    .replace(
      config['form'],
      `<a href="https://${config['form']}">${config['form']}</a>`
    )
    .replace(/\n/g, '<br>');

function firstDraft() {
  for (let i = START_IDX; i < END_IDX+1; i++) {
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
${config['form']}

Or read about the survey here.`;
const HTML_SECOND_BODY = firstName =>
  SECOND_BODY(firstName)
    .replace(
      'Reid Hoffman, founder of LinkedIn.',
      '<a href="https://en.wikipedia.org/wiki/Reid_Hoffman">Reid Hoffman, founder of LinkedIn.</a>'
    )
    .replace(
      config['form'],
      `<a href="https://${config['form']}">${config['form']}</a>`
    )
    .replace(
      'here.',
      `<a href="http://${SURVEY_PAGE}">here.</a>`
    )
    .replace(/\n/g, '<br>');

function secondDraft() {
  for (let i = START_IDX; i < END_IDX+1; i++) {
    const [company, name, title, email, status, threadID] = rows[i];
    if (status !== 'drafted_1' || !email) continue;
    const firstName = String(name).trim().split(/\s+/)[0];

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
const THIRD_BODY = firstName => `Only marketers at ${config['ranking']} firms are surveyed.

And we determine who the most innovative CMOs are entirely based on survey responses.

It takes 1 minute to anonymously answer
${config['form']}`;
const HTML_THIRD_BODY = firstName =>
  THIRD_BODY(firstName)
    .replace(
      config['form'],
      `<a href="https://${config['form']}">${config['form']}</a>`
    )
    .replace(/\n/g, '<br>');

function thirdDraft() {
  for (let i = START_IDX; i < END_IDX+1; i++) {
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