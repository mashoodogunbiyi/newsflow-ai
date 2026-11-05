# NFA-81 UAT Test Script

## Moderator rules

- Reset the mock and open a fresh private browser window before each session.
- Read only the task wording first. Do not name the button or route that completes the task.
- Record directed help as assistance and do not mark that attempt as an unqualified Pass.
- Record the actual outcome before discussing possible improvements.
- Use UAT-15 last because it enables a controlled provider failure.

## Scenarios

| ID     | Participant task                                                                                                                                                                 | Expected result                                                                                                                                                  |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UAT-01 | Sign in with the local test account supplied by the moderator.                                                                                                                   | The participant reaches the protected dashboard, sees the signed-in account, and understands that the catalogue is fixture data.                                 |
| UAT-02 | Find the available article and explain what information is shown on its card.                                                                                                    | The participant locates the synthetic article and can identify title, source, date, category, summary, attribution, and source action.                           |
| UAT-03 | Show only Technology articles, then return to the unfiltered catalogue.                                                                                                          | The category filter is understandable, the URL and result update, and clearing the filter restores the catalogue.                                                |
| UAT-04 | Select the article and decide whether it can be used for generation.                                                                                                             | The source-review page opens and the participant understands attribution, permitted summary, fixture status, and generation availability.                        |
| UAT-05 | Choose a writing tone and length, then request a LinkedIn draft.                                                                                                                 | The selected controls are clear, one mocked request completes, and the interface states that review is required and nothing was published.                       |
| UAT-06 | Replace part of the draft with your own test wording and confirm what changed.                                                                                                   | The text is editable, character feedback remains understandable, the preview updates, and source attribution or warnings remain visible.                         |
| UAT-07 | Create an illustration using any supported preferences.                                                                                                                          | The participant understands that the image is AI-generated, one controlled illustration appears, and the original becomes selected.                              |
| UAT-08 | Request another illustration and compare the available versions.                                                                                                                 | Regeneration returns Version 2, the original remains selectable, the edited draft remains unchanged, and the new version is selected by default.                 |
| UAT-09 | Review the combined post and image as if preparing it for LinkedIn.                                                                                                              | The participant can identify the edited text, selected image, source reference, AI designation, and review reminder.                                             |
| UAT-10 | Save the reviewed result to the content library.                                                                                                                                 | One private saved draft is created and the participant receives clear success or navigation feedback.                                                            |
| UAT-11 | Leave the saved item, find it in the content library, and reopen it.                                                                                                             | The saved item is discoverable and reopens with the reviewed text, source, and selected regenerated image.                                                       |
| UAT-12 | Copy the current post text and explain which version was copied.                                                                                                                 | The current edited text is copied exactly and the interface confirms the action without claiming publication.                                                    |
| UAT-13 | Download the selected illustration.                                                                                                                                              | The selected private image downloads with a safe filename and the interface confirms the action.                                                                 |
| UAT-14 | Delete the saved item, cancelling once if you want to inspect the safeguard.                                                                                                     | A confirmation is required, cancellation preserves the item, confirmation removes active access, and the library returns to its empty state.                     |
| UAT-15 | First try an incorrect password and explain the message. Later, after the moderator enables the controlled provider failure, request a draft and explain what you would do next. | Authentication gives a generic safe error. Provider failure preserves choices and presents a deliberate retry without exposing technical or private information. |
| UAT-16 | Complete the feedback questionnaire and state whether you would accept the MVP workflow for controlled release.                                                                  | The participant records ratings, concerns, suggested improvements, and an overall recommendation with a reason.                                                  |

## Suggested observations

For every scenario record:

- start and finish time if timing is being used;
- Pass, Pass with observation, Fail, Blocked, or Not run;
- number and type of moderator interventions;
- visible hesitation or repeated navigation;
- words or controls the participant misunderstood;
- expected and actual result;
- participant comment in their own words where useful; and
- follow-up action or Jira Bug link.
