# Character System Frontend Testing Guide

Use this guide after starting the Flask server from `backend` with `python app.py`.

## 1. Open The Character Workbench

1. Open `http://localhost:8080`.
2. Click `Character` in the top navigation.
3. Confirm the Character Systems page loads without a browser console error.
4. Confirm the Roster table shows active wrestlers with Brand, Alignment, Gimmick Fit, Style, and Home columns.

Expected result: the page loads data from `/api/character-system/overview`.

## 2. Test Face/Heel Alignment

1. Open the `Turn Planner` tab.
2. Select a wrestler.
3. Move the New Alignment slider to `0`.
4. Confirm the label reads `Heel (0%)`.
5. Move it to `50`.
6. Confirm the label reads `Tweener (50%)`.
7. Move it to `100`.
8. Confirm the label reads `Face (100%)`.

Expected result: the visual label updates immediately and stays between 0 and 100.

## 3. Test Alignment Turn Execution

1. In `Turn Planner`, choose a wrestler.
2. Set New Alignment to `85`.
3. Set Timing Score to `70`.
4. Set Build Quality to `8`.
5. Set Surprise Factor to `90`.
6. Confirm the projected impact shows around `80/100`.
7. Click `Execute Turn`.
8. Confirm a success alert appears.
9. Return to the `Roster` tab and verify that wrestler now shows `Face 85%`.
10. Refresh the browser and verify the value persists.

Expected result: the turn is saved in SQLite and the wrestler popularity is adjusted by the impact result.

## 4. Test Gimmick Assignment

1. Open the `Gimmicks` tab.
2. Select a wrestler.
3. Select a template such as `Monster Heel` or `Technical Specialist`.
4. Click `Assign Gimmick`.
5. Confirm the success alert shows an effectiveness percentage.
6. Return to `Roster` and verify `Gimmick Fit` updated.
7. Restart the Flask server and verify the value persists.

Expected result: `/api/character-system/wrestlers/{id}/gimmick` saves the assignment and effectiveness.

## 5. Test Entrance Production

1. Open the `Production` tab.
2. Select a wrestler.
3. Choose `full` pyro, `choreographed` lighting, `full` video, `signature` props, and `fog` effects.
4. Click `Save Entrance`.
5. Confirm the success alert includes a weekly cost and presentation boost.
6. Refresh the page and confirm no console errors.

Expected result: the entrance configuration persists in `entrance_configurations`.

## 6. Test Catchphrases And Moves

1. Open the `Moves` tab.
2. Select a wrestler.
3. Enter a Move Name.
4. Select `Finisher`.
5. Click `Save Move`.
6. Confirm a success alert.
7. Enter a catchphrase under 140 characters.
8. Click `Save Phrase`.
9. Confirm a success alert.

Expected result: finishers persist in `finisher_moves`; catchphrases persist in `catchphrases`.

## 7. Test Wrestling Style And Background

1. Open the `Background` tab.
2. Select a wrestler.
3. Set Primary Style to `technical`, `brawler`, or another style.
4. Enter Nationality and Kayfabe Hometown.
5. Click `Save Background`.
6. Return to `Roster` and verify Style and Home update.
7. Restart the server and verify the values persist.

Expected result: profile data is saved directly on the wrestler row.

## 8. Test Aging Progression

1. Open the `Aging` tab.
2. Click `Run Age Progression`.
3. Confirm the output panel shows recorded rating changes.
4. Refresh the page and verify the system remains stable.

Expected result: rating changes are persisted in `rating_history`.

## 9. Regression Checks

1. Navigate to `Booking`.
2. Confirm the booking page loads without the `renderShowInfo` null error.
3. Add an Elimination Chamber match and select fewer than six competitors.
4. Confirm the frontend blocks the save with a warning.
5. Select exactly six competitors and confirm the match can be added.
6. Run a show with an older saved Chamber draft if available.

Expected result: the simulator no longer fails with `Multi-competitor match needs 3+ wrestlers, got 2`.
