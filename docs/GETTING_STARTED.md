# Getting Started

**For parents, students, teachers and counsellors. No technical background assumed.**

This guide is shorter than you might expect, because PathAhead does not need an
AI model, a graphics card, an account or an internet connection to work. It is
a few kilobytes of data and some arithmetic.

---

## First: do you even need to install anything?

Probably not.

There is a **web version** that runs entirely inside your browser. Open the
link, use it, close the tab. Your grades are never uploaded, because there is
nowhere to upload them to — the calculation happens on your own phone or
laptop, and the page has no server behind it.

**Install the desktop version only if you want:**

- to use it with no internet at all,
- to keep a saved profile for more than one child on your own machine,
- to print or export reports,
- counsellor mode, for a whole class at once.

If none of those apply, use the web version and skip the rest of this page.

---

## Installing on your own computer

### Step 1 — Get Python (one time, free, about 5 minutes)

PathAhead is written in Python. If you have never installed it:

1. Go to **https://www.python.org/downloads/**
2. Click the big yellow **Download Python** button.
3. Run the file you downloaded.
4. **On the very first screen, tick "Add python.exe to PATH".** This matters.
   If you miss it, the installer will not find Python later.
5. Click **Install Now** and wait.

On a Mac you can also use `brew install python` if you already have Homebrew.
If that sentence meant nothing to you, use the website instead — it is fine.

### Step 2 — Download PathAhead

On the project page, click the green **Code** button, then **Download ZIP**.
Unzip it somewhere you can find again — your Documents folder is fine.

### Step 3 — Run the installer

Open the folder you just unzipped.

- **Windows:** double-click `PathAhead_Install.bat`
- **Mac or Linux:** open Terminal in that folder and run `./PathAhead_Install.sh`

A black window appears with text scrolling past. This is normal and it is not
an error. It takes about three minutes and downloads roughly 40 KB — smaller
than a photo.

When it finishes it will say **Done**.

> **If it says Python was not found:** you probably missed the "Add python.exe
> to PATH" tick box in Step 1. Reinstall Python, tick that box, and run the
> installer again.

### Step 4 — Start it

- **Windows:** double-click `PathAhead_Start.bat`
- **Mac or Linux:** run `./PathAhead_Start.sh`

Your web browser opens automatically at `localhost:8902`. That address means
"this computer" — the page is being served by your own machine and nothing is
going out to the internet.

Leave the black window open while you use PathAhead. Closing it stops the app.

---

## Using it

### The first question is the important one

> **What year is your child in now?**

That is the only question that decides which set of rules apply. In Singapore
right now, one school year can be the difference between two entirely different
rulebooks, so PathAhead reads your answer back to you in plain words:

> *Junior College 2 in 2026 means sitting the A-Level in 2026, applying for
> admission in 2027.*

If that sentence is wrong, change the year level before going any further.

### Entering grades

One row per subject: the level (H1, H2, General Paper, Mother Tongue), the
subject name, and the grade. Add or remove rows as needed.

**PathAhead never asks for a name, a school, an email or an NRIC.** Those
fields do not exist in the app. You can use the whole thing without telling it
anything about who you are.

**In a hurry, or just want to see what it looks like?** Click **Try a worked
example instead**. It fills in a realistic set of grades and shows you the
complete result in one click, with nothing to type.

### Reading the result

**Your score** is shown first. Click **"Show me how this was worked out"** and
you get every single step — which subjects counted, which were left out and
why, and where any cap was applied. If a number looks wrong, you can see
exactly where it came from.

**Two numbers, and this is important.** PathAhead shows your University
Admission Score out of 70, *and* a second figure out of 60 based only on your
three H2 grades. They are different on purpose. The universities have not yet
published any grade profile on the new 70-point basis — NUS says so directly —
so the only honest comparison against last year's published profiles is the
three H2 grades. PathAhead explains this on screen. Most calculators do not.

**Where this could lead** groups courses into three plainly named buckets:

- **At or above last year's range** — a good sign, not a guarantee.
- **Within last year's range** — inside the range of students admitted last year.
- **Below last year's range** — last year's picture, not a decision about you.

They are *ranges*, from the 10th to the 90th percentile of students admitted
**last year**. They are not pass marks, and the institutions that publish them
say so themselves.

**Getting to a particular course** works backwards. Pick a destination and you
get what it takes — and always **at least three ways there**, including
polytechnic-to-degree, aptitude-based admission, other universities, and retake
or appeal routes. PathAhead will not show you a single required score on its
own. That is a deliberate rule, not a missing feature.

---

## Questions people actually ask

**Does my child's data go anywhere?**
No. There is no account, no server, no analytics and no telemetry. The desktop
version runs on your machine; the web version runs in your browser. There is
nowhere for the data to go.

**Is this official?**
No, and it never claims to be. PathAhead is an independent open-source tool. It
is not affiliated with, endorsed by, or connected to MOE, SEAB, Cambridge
Assessment, or any school, polytechnic, ITE or university. It links to the
official page behind every number so you can check.

**How current are the numbers?**
Every screen shows the data date. Any individual figure that is past its
publication cycle is greyed out with a link to the official page — PathAhead
will not quietly show you last year's number as if it were this year's.

**A number looks wrong to me.**
Please tell us — there is a report link on every figure, and corrections from
teachers and parents are the most valuable contribution this project receives.

**Does it predict whether my child will get in?**
No, and it will not pretend to. Admission depends on this year's applicants,
this year's places, and for many courses on interviews, portfolios and tests
that no formula captures. PathAhead shows what was published and what it means.
The decision is a human one — your child's teachers and the school's Education
and Career Guidance counsellor are the right people for it.

**How do I uninstall it?**
Delete the folder. That is all — PathAhead does not install anything elsewhere,
does not add startup items, and does not leave files behind.
