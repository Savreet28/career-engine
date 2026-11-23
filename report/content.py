"""
report/content.py
=================

The report as data. Rendered to PDF and DOCX by build_report.py.

Content rules followed here:
  * Every sentence describes what the system ACTUALLY does. The earlier draft
    referred to an Anthropic Claude API, "Natural Language Generation using
    LLM" and interview "answers"; none of those exist in the delivered system,
    so they are corrected rather than carried forward.
  * The original wording is preserved wherever it was already accurate.
  * Figure numbers are unchanged so the supplied diagrams keep their labels.
"""

from build_report import (
    bold, bullet, chapter, figure, front, h2, h3, num, p, pagebreak, spacer,
    table,
)


# ---------------------------------------------------------------------------
# Front matter
# ---------------------------------------------------------------------------
def front_matter(toc, figs, tabs):
    b = [("titlepage",), pagebreak()]

    b += [front("ABSTRACT"),
          p("The AI-Powered Career Engine is an intelligent web-based system designed "
            "to help students and job seekers analyse their resumes, understand job "
            "requirements, plan what to learn next, and prepare for interviews. In "
            "today's competitive job market, candidates often find it difficult to "
            "determine how well their resume matches a particular job, identify "
            "missing skills, and prepare for questions based on their own experience. "
            "This system provides a personalised solution by analysing the candidate's "
            "resume, GitHub profile and the job description they are applying to."),
          p("The system uses Natural Language Processing techniques together with "
            "Retrieval-Augmented Generation (RAG) to extract and analyse information "
            "such as skills, projects, education and experience, and to identify what "
            "a given job actually requires. It generates an Applicant Tracking System "
            "(ATS) compatibility score out of 100 from nine transparent, rule-based "
            "components, and reports the reason and the supporting evidence for every "
            "point awarded."),
          p("For explainable job matching, job-description documents are divided into "
            "small passages, converted into dense vector embeddings using a locally "
            "executed sentence-transformer model, and indexed in a FAISS vector store. "
            "The requirements a candidate is measured against are derived from the "
            "passages retrieved for that specific role, so every requirement can be "
            "traced back to the sentence that demanded it."),
          p("The system additionally ranks the candidate against every supported job "
            "role, generates a phased learning roadmap ordered by a skill prerequisite "
            "graph, and selects interview questions matched to the candidate's own "
            "skill profile. An important design decision is that no large language "
            "model is used anywhere in the system: all scoring, matching and written "
            "output is produced by deterministic rules, which makes every result "
            "reproducible and explainable."),
          p("The AI-Powered Career Engine is useful for students, fresh graduates and "
            "job seekers preparing for internships and placements. It brings resume "
            "analysis, skill-gap identification, role recommendation, career guidance "
            "and interview preparation together in a single platform."),
          pagebreak()]

    b += [front("ACKNOWLEDGEMENT"),
          p("We are highly grateful to Dr. Satinderpal Singh, Principal, Guru Nanak "
            "Dev Engineering College (GNDEC), Ludhiana, for providing us the "
            "opportunity to carry out this major project work successfully."),
          p("The constant guidance and encouragement received from Dr. Kiran Jyoti, "
            "Head of Department, Computer Science and Engineering Department, GNDEC "
            "Ludhiana, has been of great help in carrying out the project work and is "
            "acknowledged with sincere thanks."),
          p("We would like to express our deep sense of gratitude and thanks to our "
            "respected Dr. Manpreet Kaur Mand, whose valuable guidance, continuous "
            "support and wise counsel made it possible to complete this project in an "
            "efficient manner."),
          p("We also express our gratitude to all the faculty members of the Computer "
            "Science and Engineering Department of GNDEC for their intellectual "
            "support and encouragement throughout the course of this work."),
          p("Finally, we are thankful to all those who directly or indirectly "
            "contributed towards the successful completion of this project report "
            "work."),
          spacer(10),
          p("Manpreet Kaur"), p("Savreet Kaur"), p("Mansi"),
          pagebreak()]

    b += [front("LIST OF FIGURES"),
          table("", [["Figure", "Description", "Page No."]] +
                [[k, v, figs.get(k, "")] for k, v in FIGURE_INDEX],
                [0.16, 0.66, 0.18]),
          pagebreak()]

    b += [front("LIST OF TABLES"),
          table("", [["Table", "Description", "Page No."]] +
                [[k, v, tabs.get(k, "")] for k, v in TABLE_INDEX],
                [0.16, 0.66, 0.18]),
          pagebreak()]

    b += [front("TABLE OF CONTENTS"),
          table("", [["Contents", "Page No."]] +
                [[k, toc.get(k, "")] for k in TOC_ENTRIES],
                [0.84, 0.16]),
          pagebreak()]
    return b


FIGURE_INDEX = [
    ("Fig 3.2.1", "Methodology and system architecture"),
    ("Fig 3.2.2", "DFD Level 0"),
    ("Fig 3.2.3", "DFD Level 1"),
    ("Fig 3.2.4", "E-R Diagram"),
    ("Fig 4.4.1", "Login page"),
    ("Fig 4.4.2", "Input form"),
    ("Fig 4.4.3", "Overview dashboard"),
    ("Fig 4.4.4", "ATS score breakdown"),
    ("Fig 4.4.5", "Job match breakdown"),
    ("Fig 4.4.6", "Learning roadmap"),
    ("Fig 4.4.7", "Role fit analysis"),
    ("Fig 4.4.8", "Resume and GitHub analysis"),
]

TABLE_INDEX = [
    ("Table 2.1", "Hardware and software requirements"),
    ("Table 2.2", "Summary of related work"),
    ("Table 3.1", "Skill taxonomy categories"),
    ("Table 3.2", "ATS score components and weights"),
    ("Table 3.3", "Ownership of resume facts by component"),
    ("Table 3.4", "Experience-level calibration"),
    ("Table 3.5", "Chunk distribution in the knowledge base"),
    ("Table 3.6", "Job match score components and weights"),
    ("Table 3.7", "Examples from the skill prerequisite graph"),
    ("Table 3.8", "Composition of the interview question bank"),
    ("Table 3.9", "Backend module structure"),
    ("Table 4.1", "Python libraries used"),
    ("Table 4.2", "Test cases designed"),
    ("Table 4.3", "Automated test coverage by area"),
    ("Table 4.4", "REST API endpoints"),
    ("Table 4.5", "Observed stage execution times"),
    ("Table 5.1", "Objectives and their outcomes"),
]

TOC_ENTRIES = [
    "Abstract", "Acknowledgement", "List of Figures", "List of Tables",
    "Table of Contents",
    "Chapter 1  Introduction",
    "1.1 Introduction to Project",
    "1.2 Project Category",
    "1.3 Problem Formulation",
    "1.4 Identification / Recognition of Need",
    "1.5 Existing System",
    "1.6 Objectives",
    "1.7 Proposed System",
    "1.8 Unique Features of the Proposed System",
    "1.9 Organization of the Report",
    "Chapter 2  Requirement Analysis and System Specification",
    "2.1 Feasibility Study",
    "2.2 Software Requirement Specification (SRS)",
    "2.3 Hardware and Software Requirements",
    "2.4 Review of Related Work",
    "Chapter 3  System Design",
    "3.1 Design Approach",
    "3.2 Detail Design using Structured Analysis and Design Tools",
    "3.3 Skill Taxonomy Design",
    "3.4 ATS Scoring Methodology",
    "3.5 Experience-Level Calibration",
    "3.6 Retrieval-Augmented Generation Pipeline",
    "3.7 Job Matching Methodology",
    "3.8 Career Roadmap Design",
    "3.9 Interview Preparation Design",
    "3.10 Backend Module Structure",
    "Chapter 4  Implementation and Testing",
    "4.1 Languages, IDEs, Tools and Technologies Used",
    "4.2 Testing Techniques",
    "4.3 Test Cases Designed",
    "4.4 Output Screenshots",
    "4.5 Implementation of Core Modules",
    "4.6 REST API Endpoints",
    "4.7 Results and Observations",
    "Chapter 5  Conclusion and Future Scope",
    "5.1 Conclusion",
    "5.2 Objectives Achieved",
    "5.3 Limitations of the Present System",
    "5.4 Future Scope",
    "References",
]


# ---------------------------------------------------------------------------
# Chapter 1 — Introduction
# ---------------------------------------------------------------------------
def chapter_1():
    return [
        chapter("CHAPTER 1", "INTRODUCTION"),

        h2("1.1 Introduction to Project"),
        p("In the present digital world, students and job seekers use online "
          "platforms, resumes and job portals to search for internships and "
          "employment opportunities. However, with increasing competition, candidates "
          "often find it difficult to understand whether their resume matches a "
          "particular job, which skills they are missing, and how they should prepare "
          "for the recruitment process. This creates a challenge for candidates in "
          "improving their profiles and preparing effectively for their desired roles."),
        p("A further difficulty is that the first reader of a resume is usually not a "
          "person at all. Most medium and large organisations route applications "
          "through an Applicant Tracking System, which parses the document, searches "
          "for expected fields and keywords, and ranks the result before any recruiter "
          "sees it. A candidate who is rejected at this stage receives no explanation, "
          "and therefore has no way of knowing whether the problem was a missing "
          "skill, an unreadable layout, or simply vocabulary that did not match the "
          "posting."),
        p("The AI-Powered Career Engine is developed to solve this problem by "
          "providing personalised career and job preparation support. The project "
          "analyses a candidate's resume, GitHub profile and job description to "
          "identify relevant skills, projects, experience and job requirements. It "
          "generates an ATS compatibility score along with an explanation of matching "
          "and missing skills, helping candidates understand their resume performance."),
        p("The system also ranks the candidate against every supported job role, "
          "generates a personalised career roadmap based on the identified skill gaps, "
          "and selects interview questions drawn from the candidate's own skill "
          "profile. This helps users understand what they need to learn and practise "
          "for a specific job role."),
        p("A defining characteristic of this project is that every number and every "
          "sentence it produces is computed by transparent rules rather than generated "
          "by a language model. The same resume always produces the same score, the "
          "total can be recomputed by hand from the published component weights, and "
          "each point awarded is accompanied by the literal text from the resume that "
          "earned it. This emphasis on reproducibility and explainability "
          "distinguishes the system from tools that return an unexplained number."),

        h2("1.2 Project Category"),
        p("The AI-Powered Career Engine falls under the following categories:"),
        h3("Application Based Project"),
        p("The system is developed as a practical software application that can be "
          "directly used by students and job seekers for resume analysis, ATS score "
          "evaluation, skill-gap identification, career planning and interview "
          "preparation."),
        h3("Research Based Project"),
        p("The project applies Retrieval-Augmented Generation, dense vector "
          "embeddings and similarity search to a practical problem, and evaluates "
          "design alternatives experimentally. Decisions such as the chunking "
          "strategy and the ranking basis for role recommendation were taken on the "
          "basis of measured behaviour rather than assumption, which gives the work a "
          "research dimension alongside its application value."),
        h3("Industry Based Project"),
        p("This project has practical applications in recruitment platforms, career "
          "guidance systems, placement preparation platforms, HR technologies and job "
          "portals. It can help candidates understand job requirements and improve "
          "their preparation for specific job roles."),
        p("Thus, the project can be considered a combination of Application Based, "
          "Research Based and Industry Oriented Project."),

        h2("1.3 Problem Formulation"),
        p("In today's competitive job market, students and job seekers apply for "
          "different internships and job opportunities but often find it difficult to "
          "understand whether their resume matches the requirements of a particular "
          "job. They may also be unaware of the important skills missing from their "
          "profile and the areas they need to improve."),
        p("Traditional resume checking methods mainly focus on basic formatting and "
          "keyword matching and may not provide a detailed explanation of how well a "
          "candidate matches a specific job description. Similarly, career guidance "
          "and interview preparation are often general and may not be personalised "
          "according to the candidate's resume, projects and skills."),
        p("A second limitation of existing approaches is the opacity of the result. "
          "Tools that delegate the entire judgement to a language model can produce "
          "fluent explanations, but those explanations cannot be audited: the same "
          "resume may be described differently on two runs, and no individual "
          "statement can be traced to a specific rule or a specific piece of evidence. "
          "For a tool whose purpose is to tell a student what to change, this is a "
          "serious weakness."),
        p("Therefore, there is a need for an intelligent system that can analyse a "
          "candidate's resume, GitHub profile and job description to provide a "
          "personalised assessment. The system should generate an ATS compatibility "
          "score with an explanation of matching and missing skills, suggest a "
          "suitable learning roadmap, and provide interview questions based on the "
          "candidate's own profile."),
        p("The problem is therefore to design a system that provides personalised "
          "resume analysis, job matching, skill-gap identification, career roadmap "
          "generation and interview preparation, in a manner that is efficient, "
          "user-friendly and, above all, explainable."),

        h2("1.4 Identification / Recognition of Need"),
        p("The need for this project was identified due to the increasing competition "
          "in the job market and the difficulties faced by students and job seekers "
          "during resume preparation and interview preparation. Some important "
          "reasons are:"),
        bullet("Increasing competition for internships and job opportunities."),
        bullet("Difficulty in understanding job requirements."),
        bullet("Difficulty in identifying missing skills from a resume."),
        bullet("Lack of personalised resume and job matching analysis."),
        bullet("Need for an understandable ATS score with proper explanation."),
        bullet("Difficulty in creating a suitable learning roadmap for a specific job "
               "role."),
        bullet("Need for interview questions matched to the candidate's own skills "
               "and projects."),
        bullet("Requirement of a smart, efficient and user-friendly career "
               "preparation solution."),
        p("This project fulfils the need for an intelligent system that can analyse a "
          "candidate's profile, identify skill gaps, provide personalised career "
          "guidance and support interview preparation, while keeping every result "
          "traceable to the evidence that produced it."),

        h2("1.5 Existing System"),
        p("Currently, resume evaluation and career preparation are mostly done "
          "manually by candidates, placement cells and career counsellors, or by using "
          "separate online tools for resume checking and interview preparation. Some "
          "advanced platforms use AI-based resume analysis, but they may provide "
          "limited personalisation or focus only on specific aspects such as resume "
          "scoring or job matching."),
        bold("Limitations of Existing System:"),
        bullet("Manual resume and job matching is time-consuming."),
        bullet("Candidates may not clearly understand why their resume receives a "
               "particular ATS score."),
        bullet("Difficulty in identifying specific skill gaps for a target job role."),
        bullet("Existing tools may provide general career recommendations rather than "
               "personalised roadmaps."),
        bullet("Interview preparation is often not directly based on the candidate's "
               "own resume and projects."),
        bullet("Resume analysis, career planning and interview preparation are "
               "usually available as separate services."),
        bullet("Limited integration of GitHub projects and coding profiles into "
               "career analysis."),
        bullet("Scores produced by language-model-based tools are not reproducible, "
               "so the same resume may receive different assessments on different "
               "occasions."),
        p("These limitations create the need for a better and smarter system that can "
          "provide personalised resume analysis, job matching, career guidance and "
          "interview preparation in a single platform."),

        h2("1.6 Objectives"),
        p("The main objectives of the AI-Powered Career Engine are:"),
        bullet("To develop a web application that analyses a student's resume, GitHub "
               "profile and target job role to generate an ATS score."),
        bullet("To implement a feature that uses RAG over job-description data for "
               "explainable job and role matching."),
        bullet("To provide a personalised career roadmap, role recommendations and "
               "resume-based interview preparation."),

        h2("1.7 Proposed System"),
        p("The proposed system is a web application designed to help students and job "
          "seekers analyse their career profiles and prepare for specific job roles. "
          "The system takes the candidate's resume, GitHub profile, target job role, "
          "experience level and the job description as input."),
        p("The system first analyses the uploaded resume to extract important "
          "information such as skills, education, projects, experience, resume "
          "sections, contact information, action verbs and quantified achievements. "
          "The GitHub profile is also analysed to identify technical skills and "
          "relevant repositories. These details are then used to calculate an ATS "
          "compatibility score based on skill and keyword matching, resume structure, "
          "contact information, measurable impact, readability and formatting."),
        p("For explainable job matching, job-description documents are divided into "
          "small labelled passages and indexed as vectors. For a given role the system "
          "retrieves the most relevant passages, extracts the skills named inside "
          "them, and treats those as the requirements for that role. It then compares "
          "the candidate's resume skills and GitHub skills against those requirements, "
          "identifying matched skills, missing skills and the evidence supporting "
          "each."),
        p("Based on the identified skill gaps, the system produces a personalised "
          "career roadmap that orders the missing skills by a prerequisite graph, so "
          "that foundations are learned before the skills that depend on them. It also "
          "ranks the candidate against all supported roles, and selects interview "
          "questions matched to the candidate's skill profile and experience level."),
        p("The final results are presented through an interactive web interface that "
          "includes the ATS score and its breakdown, matched and missing skills, the "
          "job-match explanation, the role-fit ranking, the career roadmap and the "
          "interview preparation set. This makes the system a practical and "
          "user-friendly solution for personalised career preparation."),

        h2("1.8 Unique Features of the Proposed System"),
        p("The AI-Powered Career Engine has several unique features:"),
        bullet("Resume, GitHub profile and target job role analysis in a single "
               "platform."),
        bullet("ATS compatibility score with a detailed, point-by-point breakdown in "
               "which every component states its reason and its evidence."),
        bullet("Identification of matched and missing skills for the selected job "
               "role."),
        bullet("Explainable job and role matching in which the requirements are "
               "derived from retrieved job-description passages rather than a "
               "hard-coded list."),
        bullet("Experience-level calibration, so that a fresher is not measured "
               "against the skill coverage expected of a senior candidate."),
        bullet("Role-fit ranking across all supported roles, identifying roles the "
               "candidate may suit better than the one chosen."),
        bullet("Personalised career roadmap ordered by a skill prerequisite graph."),
        bullet("Interview questions selected from the candidate's own skill profile, "
               "each stating what the interviewer is assessing."),
        bullet("Integration of GitHub profile information, kept separate from resume "
               "claims so that corroborated skills can be distinguished."),
        bullet("Fully deterministic operation: no language model is used, so results "
               "are reproducible and the system runs without any paid API."),

        h2("1.9 Organization of the Report"),
        p("The remainder of this report is organised as follows. "
          "<b>Chapter 2</b> presents the requirement analysis, covering the technical, "
          "economic and operational feasibility of the project, the software "
          "requirement specification, the hardware and software needed, and a review "
          "of related work in resume analysis and job matching."),
        p("<b>Chapter 3</b> describes the system design. It presents the design "
          "approach, the methodology diagram, data flow diagrams and the entity "
          "relationship diagram, and then explains in detail the skill taxonomy, the "
          "ATS scoring methodology, the experience-level calibration, the "
          "Retrieval-Augmented Generation pipeline, the job matching methodology and "
          "the design of the roadmap and interview preparation modules."),
        p("<b>Chapter 4</b> covers implementation and testing, including the "
          "languages, tools and libraries used, the testing techniques applied, the "
          "test cases designed, screenshots of the working system, the implementation "
          "of each core module, the REST API surface and the observed results."),
        p("<b>Chapter 5</b> concludes the report, states which objectives were "
          "achieved, records the limitations of the present system honestly, and "
          "outlines the scope for future work. The references consulted during the "
          "project are listed at the end."),
        pagebreak(),
    ]


# ---------------------------------------------------------------------------
# Chapter 2 — Requirement Analysis and System Specification
# ---------------------------------------------------------------------------
def chapter_2():
    return [
        chapter("CHAPTER 2", "REQUIREMENT ANALYSIS AND SYSTEM SPECIFICATION"),

        h2("2.1 Feasibility Study"),
        p("A feasibility study is conducted to determine whether the proposed project "
          "can be successfully developed and implemented. It helps in analysing the "
          "practicality of the system in terms of technical resources, cost and "
          "operational usability. For the AI-Powered Career Engine, the feasibility "
          "study is explained below."),

        h3("2.1.1 Technical Feasibility"),
        p("Technical feasibility checks whether the required technology, tools and "
          "resources are available for the project. The proposed system is technically "
          "feasible because it uses commonly available technologies such as Python, "
          "Natural Language Processing techniques, sentence-transformer embeddings, "
          "the FAISS vector search library, the GitHub REST API and modern web "
          "development frameworks. These technologies are widely used for text "
          "analysis and information retrieval applications, and all of them are "
          "open-source and free to use."),
        p("An important factor in favour of technical feasibility is that the system "
          "requires no paid external service. The embedding model used for semantic "
          "retrieval is approximately 90 MB in size and executes locally on an "
          "ordinary laptop, and a fallback retrieval method based on TF-IDF and "
          "Truncated Singular Value Decomposition is available should the model not be "
          "downloadable. The project therefore requires only a computer system with "
          "moderate specifications, an internet connection for accessing GitHub data, "
          "and a suitable Python development environment. Therefore, the project is "
          "technically feasible."),

        h3("2.1.2 Economical Feasibility"),
        p("Economical feasibility checks whether the project can be developed within a "
          "reasonable cost. The AI-Powered Career Engine is cost-effective because it "
          "uses open-source programming languages, libraries and development tools "
          "throughout. The system does not require any specialised hardware or "
          "expensive infrastructure for development."),
        p("The project can be developed using an existing personal computer and freely "
          "available development tools. Because the system deliberately avoids any "
          "commercial language-model service, there is no per-request cost and no "
          "subscription requirement, and the running cost of the deployed system is "
          "therefore effectively zero. The only optional credential is a free GitHub "
          "personal access token, which simply raises the permitted request rate. "
          "Therefore, the project is economically feasible."),

        h3("2.1.3 Operational Feasibility"),
        p("Operational feasibility checks whether the system can be easily used and "
          "accepted by users. The proposed system is designed with a simple and "
          "user-friendly interface so that students and job seekers can easily provide "
          "their resume, GitHub profile, target job role and experience level."),
        p("The system provides understandable results such as the ATS score, matching "
          "and missing skills, the job-match explanation, the role-fit ranking, the "
          "career roadmap and interview questions. Because each result is accompanied "
          "by the reason for it, a user does not need technical knowledge to act on "
          "the output. Therefore, the project is operationally feasible."),

        h2("2.2 Software Requirement Specification (SRS)"),
        p("The Software Requirement Specification document describes all functional "
          "and non-functional requirements of the system. It defines what the software "
          "should do and how it should perform. For the AI-Powered Career Engine, the "
          "requirements are described below."),

        h3("2.2.1 Data Requirement"),
        p("The system requires different types of input data for analysis:"),
        bullet("Student resume in PDF or DOCX format."),
        bullet("GitHub profile information and repository data."),
        bullet("Target job role selected by the user."),
        bullet("Experience level of the candidate."),
        bullet("Job description data for detailed job matching and analysis."),
        p("In addition to user-supplied input, the system maintains two internal data "
          "sets: a job-description knowledge base of twelve documents covering six "
          "roles, and a bank of sixty-five interview questions tagged by skill and "
          "difficulty. A skill taxonomy of one hundred and twelve canonical skills "
          "provides the shared vocabulary that allows resume text, GitHub metadata and "
          "job descriptions to be compared with one another."),

        h3("2.2.2 Functional Requirement"),
        p("Functional requirements define the main functions of the system."),
        bullet("The system should allow users to upload their resume in PDF or DOCX "
               "format."),
        bullet("The system should accept a GitHub profile for profile and repository "
               "analysis."),
        bullet("The system should allow users to select a target job role and an "
               "experience level."),
        bullet("The system should allow users to provide the job description they are "
               "applying to."),
        bullet("The system should analyse the resume and GitHub profile to identify "
               "relevant skills and projects."),
        bullet("The system should generate an ATS compatibility score out of 100."),
        bullet("The system should provide a component-wise explanation of the ATS "
               "score, stating the reason and evidence for each component."),
        bullet("The system should perform job and role matching using retrieved "
               "job-description data."),
        bullet("The system should rank the candidate against all supported job roles."),
        bullet("The system should generate a personalised career roadmap based on the "
               "identified skill gaps."),
        bullet("The system should select interview questions based on the candidate's "
               "skill profile and experience level."),
        bullet("The system should continue to produce a result when GitHub analysis "
               "fails, degrading gracefully rather than aborting."),

        h3("2.2.3 Performance Requirement"),
        p("The performance requirements define the speed and efficiency of the "
          "system."),
        bullet("The system should process resume and GitHub information efficiently."),
        bullet("The complete analysis pipeline should finish within a few seconds for "
               "a typical resume."),
        bullet("Job matching and skill-gap analysis should be completed without "
               "unnecessary delay."),
        bullet("The vector index should be constructed once and reused across "
               "requests rather than rebuilt per analysis."),
        bullet("The system should report genuine progress for each pipeline stage "
               "rather than an estimated or simulated indicator."),

        h3("2.2.4 Maintainability Requirement"),
        p("Maintainability means the system should be easy to update, modify and "
          "improve."),
        bullet("New job roles and job-description documents can be added to the "
               "knowledge base, after which the index rebuilds automatically."),
        bullet("The ATS scoring criteria and component weights are defined in one "
               "place and can be modified without touching the scoring logic."),
        bullet("The skill taxonomy, the prerequisite graph and the interview question "
               "bank are data files that can be extended independently of the code."),
        bullet("The system has a modular and understandable code structure in which "
               "each module performs one task."),
        bullet("An automated test suite protects the behaviour of each module when "
               "changes are made."),

        h3("2.2.5 Reliability and Error-Handling Requirement"),
        p("The system must behave predictably when given unexpected input. An "
          "unsupported file type, an empty file, a file that is merely named as a PDF, "
          "a scanned image with no text layer, an unknown GitHub username, an "
          "exhausted API rate limit or a network failure must each produce a specific "
          "and actionable message rather than an unhandled error. Failures in the "
          "optional GitHub stage must degrade the analysis rather than prevent it, so "
          "that a user without a GitHub account still receives a complete result."),

        h3("2.2.6 Security and Privacy Requirement"),
        p("The system processes personal documents and must therefore handle them "
          "carefully. Resumes are parsed in memory and are not persisted to disk. No "
          "user data is transmitted to any third-party analysis service, which is a "
          "direct consequence of the decision to avoid external language-model APIs. "
          "Only publicly available GitHub information is retrieved, and any access "
          "token is read from a local environment file that is excluded from version "
          "control."),

        h2("2.3 Hardware and Software Requirements"),
        p("The hardware and software required to develop and run the system are "
          "summarised in Table 2.1. The requirements are modest because all processing "
          "is performed locally and the embedding model used is small."),
        table("Table 2.1: Hardware and software requirements", [
            ["Category", "Requirement"],
            ["Processor", "Intel Core i3 or equivalent and above"],
            ["Memory (RAM)", "4 GB minimum, 8 GB recommended"],
            ["Disk space", "Approximately 2 GB, including the Python environment and "
                           "the embedding model"],
            ["Operating system", "Windows 10/11, macOS or Linux"],
            ["Backend runtime", "Python 3.10 or above"],
            ["Frontend runtime", "Node.js 18 or above"],
            ["Browser", "Any modern browser supporting ECMAScript 2020"],
            ["Network", "Required for GitHub access and for the one-time model "
                        "download"],
        ], [0.26, 0.74]),

        h2("2.4 Review of Related Work"),
        p("Automated resume analysis has been studied from two broad directions. The "
          "first treats the problem as information extraction, applying Natural "
          "Language Processing to recover structured fields such as skills, education "
          "and experience from an unstructured document. Work on resume parsing using "
          "NLP demonstrates that rule-based and statistical extraction can recover "
          "these fields with useful accuracy, and layout-aware parsing systems show "
          "that respecting the visual structure of a document improves extraction "
          "quality compared with treating it as a flat stream of text."),
        p("The second direction treats the problem as matching, in which a candidate "
          "profile and a job description are compared to estimate suitability. Early "
          "approaches relied on keyword overlap, which is simple and transparent but "
          "fails when the two documents use different vocabulary for the same concept. "
          "The introduction of dense vector embeddings addressed this by representing "
          "text in a space where semantic similarity corresponds to geometric "
          "proximity, allowing a requirement and a candidate's description of the same "
          "capability to be matched despite different wording."),
        p("More recent work applies Retrieval-Augmented Generation to this domain. "
          "Rather than relying on a model's internal knowledge, relevant passages are "
          "retrieved from a document collection and used as the basis for the "
          "subsequent analysis. Studies applying RAG to resume analysis and job "
          "matching report that grounding the comparison in retrieved text improves "
          "both relevance and the ability to justify a result."),
        p("A parallel strand of research emphasises explainability. Systems described "
          "in the literature on explainable job recommendation and on skill-gap "
          "analysis argue that a recommendation is of limited practical value unless "
          "the recipient can see why it was made. This concern directly motivates the "
          "present work: the reviewed systems demonstrate the value of semantic "
          "retrieval, but several of them delegate the final judgement to a generative "
          "model, which reintroduces the opacity that explainability was intended to "
          "remove."),
        p("The gap identified from this review, and addressed by this project, is "
          "therefore the combination of semantic retrieval with fully deterministic "
          "scoring. Table 2.2 summarises how the reviewed directions relate to the "
          "present work."),
        table("Table 2.2: Summary of related work", [
            ["Direction", "Contribution", "Limitation addressed here"],
            ["Resume parsing using NLP",
             "Extraction of structured fields from unstructured resumes",
             "Extraction alone does not tell a candidate what to change"],
            ["Layout-aware parsing",
             "Improved extraction by respecting document structure",
             "Adopted here through section-aware segmentation"],
            ["Keyword-based matching",
             "Simple and transparent comparison",
             "Fails across differing vocabulary; addressed by embeddings"],
            ["Embedding-based matching",
             "Semantic similarity independent of wording",
             "Similarity alone does not identify which skill is missing"],
            ["RAG for resume and job matching",
             "Grounds analysis in retrieved job-description text",
             "Adopted here, but scoring is kept outside the model"],
            ["Explainable recommendation",
             "Argues that justification is essential",
             "Realised fully here by removing generative components"],
        ], [0.24, 0.40, 0.36]),
        pagebreak(),
    ]


# ---------------------------------------------------------------------------
# Chapter 3 — System Design
# ---------------------------------------------------------------------------
def chapter_3():
    return [
        chapter("CHAPTER 3", "SYSTEM DESIGN"),

        h2("3.1 Design Approach"),
        p("The design approach used for the AI-Powered Career Engine is mainly "
          "Function Oriented Design. In this approach, the system is divided into "
          "different functional modules, where each module performs a specific task. "
          "All modules work together to analyse the candidate's profile and provide "
          "personalised career and job preparation results."),
        p("The project is divided into the following functional modules:"),
        bullet("Resume Analysis Module"),
        bullet("GitHub Profile Analysis Module"),
        bullet("Job Description Retrieval Module"),
        bullet("ATS Score Generation Module"),
        bullet("Job and Role Matching Module"),
        bullet("Role Recommendation Module"),
        bullet("Career Roadmap Module"),
        bullet("Interview Preparation Module"),
        bullet("Summary Generation Module"),
        p("This approach is suitable because the project follows a step-by-step "
          "workflow in which user information is collected, analysed, matched with job "
          "requirements, and converted into personalised recommendations. Each module "
          "performs a specific function and can be developed, tested and maintained "
          "independently."),
        p("A design principle applied consistently across these modules is that each "
          "stage consumes only structured data produced by the previous stage. The "
          "matching module never sees the raw resume text; it sees the list of skills "
          "the parser extracted. The summary module never sees the job description; it "
          "sees the computed scores. This separation is what makes each stage testable "
          "in isolation and prevents any later stage from inventing information that "
          "an earlier stage did not establish."),

        h2("3.2 Detail Design using Structured Analysis and Design Tools"),

        h3("3.2.1 Methodology"),
        figure("fig_3_2_1_methodology.png", "Fig 3.2.1: Methodology", 5.6),
        bold("Explanation:"),
        p("The above figure illustrates the overall methodology and system "
          "architecture of the proposed AI-Powered Career Engine, which is designed to "
          "analyse a candidate's professional profile and provide personalised career "
          "guidance."),
        p("The system begins with an input layer where the candidate provides the "
          "major inputs: a resume in PDF or DOCX format, a GitHub profile, the target "
          "job role and the job description. These inputs are submitted through a "
          "frontend dashboard developed using React. The frontend communicates with "
          "the backend, developed using FastAPI, through API requests and receives the "
          "processed results in JSON format."),
        p("The backend coordinates the processing modules to perform the required "
          "analysis:"),
        num("1. <b>Resume Parser:</b> Extracts important information from the uploaded "
            "resume, including skills, education, projects and work experience. It "
            "also cleans and structures the extracted data for further processing."),
        num("2. <b>GitHub Analyzer:</b> Analyses the candidate's GitHub repositories, "
            "programming languages and repository topics to identify evidence of "
            "practical development experience."),
        num("3. <b>Job Description Retriever:</b> Retrieves the passages of stored job "
            "descriptions that are most relevant to the selected role, using semantic "
            "similarity search over vector embeddings."),
        num("4. <b>RAG-Powered Matcher:</b> Derives the role's requirements from the "
            "retrieved passages and compares them against the candidate's resume and "
            "GitHub evidence, identifying matched and missing skills together with the "
            "evidence for each."),
        num("5. <b>ATS Scorer:</b> Evaluates the parsed resume against nine weighted "
            "rules to calculate an ATS score, reporting the reason and evidence for "
            "every component."),
        p("After processing, the system provides the following outputs:"),
        bullet("<b>Explainable Job Matching:</b> Explanations of why the candidate "
               "matches a particular job role, including matched skills, missing "
               "skills and the job-description sentence behind each requirement."),
        bullet("<b>Role Fit Analysis:</b> A ranking of all supported roles by how much "
               "of each role's core requirements the candidate can evidence."),
        bullet("<b>Personalised Career Roadmap:</b> A phased plan of the skills to "
               "develop, ordered so that prerequisites are learned first."),
        bullet("<b>Interview Preparation:</b> Questions selected for the candidate's "
               "skill profile, each stating what the interviewer is assessing."),
        p("Finally, all the analysed information is presented through a results "
          "dashboard, which includes the ATS score, the match score, the detailed "
          "breakdowns, the skill-by-skill analysis, the role-fit ranking, the career "
          "roadmap and the interview preparation set."),

        h3("3.2.2 Data Flow Diagram (DFD Level 0)"),
        figure("fig_3_2_2_dfd0.png", "Fig 3.2.2: DFD Level 0", 5.6),
        bold("Explanation:"),
        bullet("The candidate provides a resume, GitHub username, target job role, "
               "experience level and job description."),
        bullet("The Career Engine processes the provided information."),
        bullet("The system communicates with the GitHub REST API to retrieve "
               "repository and profile information."),
        bullet("The system queries the local job-description knowledge base through "
               "the vector index to retrieve relevant requirement passages."),
        bullet("Finally, the candidate receives an ATS score report, a job-match "
               "analysis, a role-fit ranking, a personalised career roadmap and an "
               "interview preparation set."),

        h3("3.2.3 Data Flow Diagram (DFD Level 1)"),
        figure("fig_3_2_3_dfd1.png", "Fig 3.2.3: DFD Level 1", 5.6),
        bold("Explanation of processes:"),
        num("<b>1.0 Parse Resume:</b> Extracts skills, education, projects and "
            "experience from the uploaded resume."),
        num("<b>2.0 Analyze GitHub:</b> Analyses GitHub repositories, programming "
            "languages, topics and descriptions."),
        num("<b>3.0 Retrieve Job Requirements:</b> Retrieves the job-description "
            "passages most relevant to the target role and extracts the required "
            "skills named within them."),
        num("<b>4.0 Compute ATS and Match:</b> Compares candidate skills and "
            "evidence with job requirements to calculate the ATS and job-match "
            "scores."),
        num("<b>5.0 Rank Roles and Build Roadmap:</b> Scores the candidate against "
            "every role and orders the remaining skill gaps into a phased plan."),
        num("<b>6.0 Generate Career Outputs:</b> Selects interview questions and "
            "assembles the written summary of the computed results."),
        bold("Data Stores:"),
        bullet("D1 – Candidate Data"),
        bullet("D2 – Skills Taxonomy and Scoring Rules"),
        bullet("D3 – Job Description Knowledge Base and Vector Index"),
        bullet("D4 – Analysis Results"),

        h3("3.2.4 Database Design (E-R Diagram)"),
        figure("fig_3_2_4_er.png", "Fig 3.2.4: E-R Diagram", 5.6),
        bold("Explanation (entities and relationships):"),
        bullet("<b>Candidate:</b> Stores candidate details such as candidate ID, name "
               "and email."),
        bullet("<b>Resume:</b> Stores uploaded resume files and extracted "
               "information."),
        bullet("<b>Resume Skill:</b> Stores skills extracted from the candidate's "
               "resume."),
        bullet("<b>GitHub Profile:</b> Stores GitHub username and profile "
               "information."),
        bullet("<b>Repository:</b> Stores repository details, programming languages "
               "and project information."),
        bullet("<b>Job:</b> Stores the target job role and job description."),
        bullet("<b>Job Required Skill:</b> Stores skills required for the selected "
               "job role."),
        bullet("<b>Analysis Report:</b> Stores the ATS score, job-match score, "
               "matched skills, missing skills and explanations."),
        bullet("<b>Report Skill Match:</b> Records the matching status and evidence "
               "for individual job requirements."),
        bullet("<b>Roadmap Item:</b> Stores recommended skills, learning activities "
               "and career improvement steps."),
        bullet("<b>Interview Question:</b> Stores the interview questions associated "
               "with each skill."),

        h2("3.3 Skill Taxonomy Design"),
        p("The single most important design decision in the system is that resume "
          "text, GitHub metadata, job descriptions and interview questions are all "
          "resolved to the same vocabulary of skill names. Without this, the statement "
          "\"Python appears in the resume\" and the statement \"Python is required by "
          "the job\" would refer to two different strings that merely look alike, and "
          "no reliable comparison would be possible."),
        p("The taxonomy defines one hundred and twelve canonical skills. Each skill "
          "has one canonical name and a list of aliases: \"JavaScript\" also matches "
          "\"js\" and \"ecmascript\", and \"React\" also matches \"reactjs\" and "
          "\"react.js\". Matching is performed with word-boundary regular expressions "
          "rather than plain substring search, which prevents several classes of false "
          "positive that would otherwise corrupt every downstream result."),
        p("Three such cases are worth recording. A plain substring search for "
          "\"Java\" matches inside \"JavaScript\"; the boundary expression prevents "
          "this. The language \"Go\" is an ordinary English word, so it is matched "
          "case-sensitively and the sentence \"we go to production\" does not award "
          "it. The letter \"R\" would be matched inside \"R&D\", so the boundary "
          "definition excludes the ampersand. Each of these was discovered during "
          "testing and is now protected by an automated test."),
        p("Skills are grouped into categories, which allows the scoring module to "
          "reward breadth across different kinds of technology rather than depth in a "
          "single one. The categories are listed in Table 3.1."),
        table("Table 3.1: Skill taxonomy categories", [
            ["Category", "Description", "Examples"],
            ["Language", "Programming languages", "Python, Java, JavaScript, C++"],
            ["Frontend", "Browser-side technologies", "React, CSS, Tailwind CSS"],
            ["Backend", "Server-side frameworks and concepts",
             "FastAPI, Django, REST APIs"],
            ["Data", "Databases and data handling", "SQL, PostgreSQL, Pandas"],
            ["Machine Learning", "Modelling and AI techniques",
             "PyTorch, NLP, Embeddings"],
            ["DevOps", "Deployment and operations", "Docker, Kubernetes, CI/CD"],
            ["Tool", "Development practice and tooling",
             "Git, Software Testing, Agile"],
            ["Concept", "Computer science fundamentals",
             "Data Structures, System Design"],
        ], [0.20, 0.42, 0.38]),

        h2("3.4 ATS Scoring Methodology"),
        p("An Applicant Tracking System is not intelligent. It opens a document, "
          "attempts to locate expected fields, searches for keywords drawn from the "
          "job posting, and ranks the result. Modelling this behaviour with explicit "
          "rules rather than a learned model gives three properties that are essential "
          "to the purpose of this project."),
        bullet("<b>Deterministic:</b> the same resume always produces the same score."),
        bullet("<b>Reproducible:</b> the total can be recomputed by hand from the "
               "published component weights."),
        bullet("<b>Explainable:</b> every point belongs to a named component that "
               "states its reason and the literal text that earned it."),
        p("The score is computed out of 100 from the nine components shown in "
          "Table 3.2. The reported total is, by construction, the arithmetic sum of "
          "the component scores; no additional adjustment is applied."),
        table("Table 3.2: ATS score components and weights", [
            ["Component", "Max", "What the component owns"],
            ["Contact Information", "10",
             "Email 3, phone 2, name 2, LinkedIn 2, GitHub link 1"],
            ["Skills", "15",
             "Labelled skills section 3, number of skills 8, category diversity 4"],
            ["Target Role Relevance", "18",
             "Coverage of the skills the selected role requires"],
            ["Job Description Keywords", "20",
             "Coverage of the skill keywords present in this posting"],
            ["Experience and Projects", "14",
             "Labelled section 4, entry count and technical detail 10"],
            ["Education", "8",
             "Labelled section 3, entry 2, degree 2, CGPA or percentage 1"],
            ["Quantifiable Achievements", "5",
             "Labelled section 1, lines carrying a measurable figure 4"],
            ["Formatting and Readability", "5",
             "Summary section, bullet usage, action verbs, length"],
            ["GitHub Profile Evidence", "5",
             "Public profile, original repositories, descriptions, relevant skills"],
            ["<b>Total</b>", "<b>100</b>", "<b>The sum of the nine components</b>"],
        ], [0.30, 0.10, 0.60]),
        p("The weights are not arbitrary. Contact Information and Formatting model "
          "what an ATS parser requires: if the software cannot locate an email address "
          "or interpret the headings, no other quality matters. Job Description "
          "Keywords carries the largest single weight because matching the specific "
          "posting is the closest analogue to how real ranking operates, and Target "
          "Role Relevance generalises the same idea to the role. The remaining "
          "components reward the substance that a human reviewer examines once the "
          "parser has admitted the document."),
        p("GitHub Profile Evidence is deliberately limited to five points. A genuine "
          "Applicant Tracking System never sees a GitHub profile, so weighting it "
          "heavily would make the score less faithful to the process it models. It is "
          "included because the project's stated input includes GitHub, and it is kept "
          "as a small, clearly separated component rather than being blended into the "
          "resume components."),
        h3("3.4.1 The Principle of One Fact, One Component"),
        p("An earlier version of the scoring model contained a separate component "
          "that awarded points for the presence of an Education section, a Skills "
          "section and so on. The Education, Skills and Experience components then "
          "awarded points for the very same sections again. A single fact about the "
          "resume therefore moved the total twice, which made the score impossible to "
          "reason about and inflated well-structured resumes without justification."),
        p("The design was corrected so that every fact is owned by exactly one "
          "component. The presence of a labelled section is scored inside the "
          "component that owns that content, as shown in Table 3.3. The Summary "
          "section is a structural signal rather than subject content, and is "
          "therefore owned by Formatting and Readability."),
        table("Table 3.3: Ownership of resume facts by component", [
            ["Fact about the resume", "Owned by"],
            ["Labelled Skills section, skill count, category diversity", "Skills"],
            ["Labelled Education section, degree, CGPA", "Education"],
            ["Labelled Experience or Projects section, entries", "Experience and Projects"],
            ["Labelled Achievements section, quantified lines", "Quantifiable Achievements"],
            ["Summary section, bullets, action verbs, length", "Formatting and Readability"],
            ["Name, email, phone, LinkedIn, GitHub link", "Contact Information"],
        ], [0.58, 0.42]),
        p("This property is enforced by the automated test suite. Removing any single "
          "section from a parsed resume must change exactly one component score, and "
          "it must be the component that owns that section. Any future change that "
          "reintroduces double counting will therefore cause a test failure."),

        h2("3.5 Experience-Level Calibration"),
        p("A final-year student will never evidence every skill named in a job "
          "description. Measuring a fresher against the coverage expected of a senior "
          "candidate produces a number that is accurate in arithmetic but meaningless "
          "in interpretation: a candidate matching twenty of fifty-five requirements "
          "is performing well for their stage, not badly."),
        p("A naive remedy would be to award bonus points to freshers. This was "
          "rejected because any such bonus is arbitrary and cannot be defended. The "
          "approach adopted instead changes the expectation rather than the "
          "arithmetic. Each experience level declares the coverage at which a "
          "component earns full marks, and coverage is scored relative to that "
          "target:"),
        bold("scaled_coverage = min(1.0, actual_coverage / expected_coverage)"),
        p("The calibration values are given in Table 3.4. A candidate covering "
          "thirty-six per cent of a role's requirements therefore scores 36/50, or "
          "seventy-two per cent of the available points, as a fresher, and 36/85, or "
          "forty-two per cent, as a senior candidate. The weights, the components and "
          "the arithmetic are identical at every level; only the expectation differs."),
        table("Table 3.4: Experience-level calibration", [
            ["Experience level", "Coverage for full marks", "Skills for full breadth",
             "Quantified achievements", "Experience / Projects split"],
            ["Fresher (0–1 years)", "50%", "10", "2", "3 / 7"],
            ["2–4 years", "70%", "15", "3", "5 / 5"],
            ["5+ years", "85%", "20", "4", "5 / 5"],
        ], [0.24, 0.20, 0.20, 0.18, 0.18]),
        p("Calibration is applied only to components that measure coverage. "
          "Structural components do not vary with career stage, because a missing "
          "email address is equally missing at any level. The Experience and Projects "
          "split also varies: a fresher rarely has formal employment, so projects "
          "carry seven of that component's ten points instead of five, while "
          "internships continue to count as experience."),
        p("One component is deliberately excluded from calibration. Evidence "
          "Corroboration, described in Section 3.7, measures whether a claimed skill "
          "is also visible in public code. That property does not become easier to "
          "satisfy with years of experience, so scaling it would amount to unjustified "
          "leniency rather than fair calibration."),
        pagebreak(),
    ]


def chapter_3b():
    return [
        h2("3.6 Retrieval-Augmented Generation Pipeline"),
        p("Retrieval-Augmented Generation is the practice of retrieving relevant "
          "documents from a collection and performing the subsequent analysis on those "
          "documents, rather than relying on knowledge held inside a model. In this "
          "project it means that the requirements a candidate is measured against are "
          "read out of real job descriptions, not written into the program as a fixed "
          "list. This is the technical core of the second objective."),
        p("The pipeline has five stages: document loading, chunking, embedding, "
          "indexing and retrieval. Each is described below."),

        h3("3.6.1 Document Loading and Chunking"),
        p("The knowledge base holds twelve job-description documents in JSON format, "
          "two for each of the six supported roles. Each document retains explicit "
          "fields for required skills, preferred skills, responsibilities, "
          "qualifications and an overview. The structure is preserved rather than "
          "flattened, because where a requirement appears determines how strongly it "
          "counts: a skill named under required skills is a must-have, whereas the "
          "same skill under preferred skills is not."),
        p("Each bullet becomes a single chunk, since a bullet already expresses one "
          "idea. Continuous prose is divided into overlapping windows of seventy words "
          "with a fifteen-word overlap, so that a sentence spanning a boundary is "
          "still fully represented in at least one chunk."),
        p("Chunking is necessary because an embedding represents the average meaning "
          "of whatever text it is given. If an entire six-hundred-word document were "
          "converted into a single vector, that vector would sit in the average of "
          "every topic the document covers, and a query about required Python skills "
          "would match the whole document without indicating which part was relevant. "
          "Small chunks keep one idea per vector, which makes retrieval precise and, "
          "equally importantly, keeps the retrieved text short enough to display to "
          "the user as evidence. The resulting distribution of chunks is shown in "
          "Table 3.5."),
        table("Table 3.5: Chunk distribution in the knowledge base", [
            ["Source section", "Chunks", "Requirement strength"],
            ["Required skills", "76", "Core"],
            ["Preferred skills", "78", "Preferred"],
            ["Responsibilities", "68", "Preferred"],
            ["Qualifications", "27", "Preferred"],
            ["About the role", "12", "Context"],
            ["<b>Total</b>", "<b>261</b>", ""],
        ], [0.40, 0.22, 0.38]),

        h3("3.6.2 Embeddings"),
        p("An embedding model converts a piece of text into a fixed-length vector of "
          "real numbers, here of length 384. The model is trained so that texts with "
          "similar meaning are mapped to nearby points in that space. This is why the "
          "query \"vector database embeddings\" retrieves the sentence \"Experience "
          "with vector databases such as FAISS, Chroma, Pinecone or Qdrant\" even "
          "though the two share almost no words."),
        p("The model used is all-MiniLM-L6-v2, a six-layer sentence-transformer of "
          "approximately ninety megabytes that executes locally. It is the only "
          "machine-learning model in the entire system, and it is not generative: it "
          "cannot produce text, only convert text into numbers for comparison."),
        p("Every vector produced is normalised to unit length. This is not a "
          "cosmetic step. For unit vectors the inner product of two vectors is "
          "exactly their cosine similarity, which allows the vector store to use a "
          "simple inner-product search while still performing cosine search. Cosine "
          "similarity between vectors A and B is defined as the dot product of A and B "
          "divided by the product of their magnitudes; when both magnitudes equal one, "
          "the denominator vanishes and the dot product alone gives a value between "
          "minus one and one, where one indicates identical direction and therefore "
          "maximum semantic similarity."),

        h3("3.6.3 Vector Store and Index Construction"),
        p("The 261 chunk vectors are stored in FAISS, a local similarity-search "
          "library that requires no server and no network access. The index type used "
          "is IndexFlatIP. The word Flat indicates that vectors are stored as they are "
          "and every query is compared against all of them, which makes the search "
          "exact rather than approximate; at this corpus size the cost of doing so is "
          "negligible. The letters IP indicate inner product, which, as explained "
          "above, equals cosine similarity for normalised vectors."),
        p("The index and its chunk metadata are written to disk and reused on "
          "subsequent runs, so the embedding step is performed once rather than on "
          "every request. The stored index records a hash of the corpus and the name "
          "of the embedding model; if either changes, the index is rebuilt "
          "automatically. This guard matters because vectors produced by one model are "
          "meaningless to another, and silently mixing them would corrupt retrieval "
          "without producing any visible error."),

        h3("3.6.4 Query Construction and Retrieval"),
        p("A role title alone is a weak query of two or three words. The query is "
          "therefore expanded, a standard information-retrieval technique: any job "
          "description the user has pasted is placed first, since it is the strongest "
          "available signal of what this particular employer wants; a small number of "
          "catalogue skills for the role follow, placing the query in the same "
          "vocabulary region as the chunks it should match; and intent words about "
          "skills and tools complete it."),
        p("Results are filtered by role identifier and diversified so that evidence "
          "is drawn from more than one employer rather than concentrating on whichever "
          "document happens to rank highest. The matching module reads a deeper slice "
          "of twenty-four chunks than the eight displayed to the user, because a small "
          "number of passages names too few skills to compute a reliable coverage "
          "ratio."),

        h3("3.6.5 An Experimentally Determined Design Decision"),
        p("An earlier version of the chunker prefixed every chunk with its job title, "
          "company and section, on the assumption that making each vector "
          "self-describing would improve retrieval. Measurement showed the opposite. "
          "For the query \"vector database embeddings\", the correct passage fell from "
          "a cosine similarity of 0.58 to 0.30 once prefixed, and an unrelated passage "
          "about SQL database schemas outranked it. The explanation is that on a short "
          "chunk the prefix contributes a large share of the averaged representation "
          "and dilutes the sentence that matters."),
        p("The prefix was therefore removed, and role scoping is achieved through the "
          "metadata filter instead. This decision is recorded here because it "
          "illustrates the value of measuring a design assumption rather than "
          "accepting it."),

        h3("3.6.6 Offline Fallback"),
        p("If the sentence-transformer model cannot be loaded, typically because no "
          "internet connection is available on first use, the system automatically "
          "substitutes a classical method: term frequency-inverse document frequency "
          "weighting reduced by Truncated Singular Value Decomposition, which is "
          "Latent Semantic Analysis. This requires no download and is fully "
          "deterministic. It is weaker at recognising paraphrase, but the entire "
          "pipeline continues to function, and the active backend is reported through "
          "the status endpoint so the difference is never hidden."),

        h2("3.7 Job Matching Methodology"),
        p("The matching module enforces the central rule of the project: the system "
          "does not submit a resume and a job description to a model and ask whether "
          "they match. Instead the requirement set is derived from the retrieved "
          "passages, the candidate's evidence is collected from the resume and GitHub "
          "separately, and the two are compared using a published formula."),

        h3("3.7.1 Deriving Requirements"),
        p("Each retrieved passage is scanned using the skill taxonomy. A skill named "
          "in a required-skills passage becomes a core requirement. Skills appearing "
          "in preferred-skills, responsibilities or qualifications passages become "
          "preferred requirements. A skill is not promoted to core merely because the "
          "posting mentions it somewhere: a technology listed under \"nice to have\" "
          "remains a nice-to-have."),
        p("When the user pastes a job description there are no JSON fields to read, "
          "so headings are detected as the text is chunked. Bullets beneath headings "
          "such as \"Required skills\" or \"Must have\" are treated as core, while "
          "bullets beneath \"Nice to have\", \"Preferred\" or \"Qualifications\" are "
          "treated as preferred."),

        h3("3.7.2 Separation of Evidence Sources"),
        p("Evidence from the resume and evidence from GitHub are recorded separately "
          "and never merged. A skill found only on GitHub is labelled as such, and the "
          "interface distinguishes resume-only, GitHub-only and corroborated skills. A "
          "skill appearing in both is a claim supported by public code, which is "
          "stronger evidence than either source alone."),
        p("Every item of GitHub evidence also records why it matched, for example "
          "\"Topic 'react' on repository X\" or \"Primary language of four "
          "repositories\". This matters because a repository description that mentions "
          "a technology is not proof of proficiency, and the system states the basis "
          "of its claim rather than overstating it."),

        h3("3.7.3 The Match Score"),
        p("The match score is a fixed weighted sum of four coverage ratios, as shown "
          "in Table 3.6. The first three are calibrated by experience level exactly as "
          "the ATS components are; the fourth is not, for the reason given in Section "
          "3.5."),
        table("Table 3.6: Job match score components and weights", [
            ["Component", "Max", "What it measures"],
            ["Core skill coverage", "55",
             "Share of must-have requirements the candidate can evidence"],
            ["Preferred skill coverage", "20",
             "Share of nice-to-have requirements evidenced"],
            ["Retrieved requirement coverage", "15",
             "Coverage measured only against the passages retrieved for this query"],
            ["Evidence corroboration", "10",
             "Share of matched skills appearing in both the resume and GitHub"],
            ["<b>Total</b>", "<b>100</b>", "<b>The sum of the four components</b>"],
        ], [0.30, 0.10, 0.60]),
        p("The headline verdict considers core coverage in addition to the total, so "
          "that a candidate cannot be described as a strong match by accumulating "
          "nice-to-have skills while missing the essential ones."),

        h3("3.7.4 Traceability of Each Requirement"),
        p("Every requirement in the result carries the reason it is required, the "
          "job-description sentence that demanded it, the sources of the candidate's "
          "evidence and the retrieval similarity that produced it. When several "
          "sentences mention a skill, the system prefers the posting the user supplied "
          "over a sample document, then a required-skills line over a nice-to-have "
          "line, and finally the closest match. This ordering ensures the displayed "
          "justification is the most relevant one available rather than merely the "
          "first encountered."),

        h2("3.8 Career Roadmap Design"),
        p("The matching module produces a set of missing skills. A set is a "
          "diagnosis, not a plan: advising a candidate to learn PyTorch is of no use "
          "if they do not yet know Python. The roadmap module converts the set into an "
          "ordered sequence using three signals, each of which is derived from data "
          "rather than invented."),
        bullet("<b>Prerequisites:</b> a directed graph of eighty-seven edges recording "
               "which skills must be learned before others."),
        bullet("<b>Demand:</b> the retrieval similarity scores already computed by the "
               "matching module, so that the most insistently requested skills lead "
               "within a phase."),
        bullet("<b>Requirement level:</b> core requirements before preferred ones."),
        p("The graph is validated automatically for cycles, for self-references and "
          "for skills that do not exist in the taxonomy; a cycle would make the "
          "instruction to learn one thing before another meaningless. Representative "
          "edges are shown in Table 3.7."),
        table("Table 3.7: Examples from the skill prerequisite graph", [
            ["Skill", "Requires first", "Depth"],
            ["CSS", "HTML", "1"],
            ["React", "JavaScript, HTML, CSS", "2"],
            ["Next.js", "React", "3"],
            ["Machine Learning", "Python, Statistics", "1"],
            ["Deep Learning", "Machine Learning", "2"],
            ["PyTorch", "Deep Learning", "3"],
            ["LLMs", "Deep Learning, NLP", "3"],
            ["RAG", "LLMs, Embeddings", "4"],
            ["Kubernetes", "Docker", "1"],
            ["System Design", "Data Structures, Algorithms, Database Design", "2"],
        ], [0.26, 0.56, 0.18]),
        p("The plan is divided into three phases. The first contains the foundations, "
          "that is, the skills on which other missing skills depend. The second "
          "contains the remaining core requirements, and the third the "
          "differentiators. Within a phase, shallower skills precede deeper ones and "
          "ties are broken by demand."),
        h3("3.8.1 Hidden Prerequisites"),
        p("A missing skill frequently depends on another skill that the candidate "
          "also lacks but which no job description named, because employers assume it. "
          "A candidate missing PyTorch may also be missing Deep Learning, which no "
          "posting lists explicitly. The roadmap identifies these, places them at the "
          "head of the plan and labels them as assumed knowledge. Omitting them is "
          "precisely how a learning plan fails in practice."),
        h3("3.8.2 Closure Under Prerequisites"),
        p("Each phase displays a limited number of steps so that the plan remains "
          "workable. An early version applied this limit directly, which produced a "
          "plan whose second phase referred to a skill as a blocker while that skill "
          "appeared nowhere in the plan, having been removed by the limit. The limit "
          "is now relaxed wherever removing a step would leave a later step blocked by "
          "something absent, so the displayed plan is always self-contained. Automated "
          "tests assert both that no step is blocked by an absent skill and that "
          "prerequisites always precede the skills that depend on them."),
        h3("3.8.3 Absence of Time Estimates"),
        p("The roadmap deliberately contains no estimate of how long a skill takes to "
          "learn. Such a figure would depend entirely on the individual learner, and "
          "nothing in the analysis supports it; presenting one would be invented "
          "precision of exactly the kind this project sets out to avoid. Each skill "
          "instead carries a depth value computed from the prerequisite graph, which "
          "is a genuine derived property of the data."),

        h2("3.9 Interview Preparation Design"),
        p("The interview module selects questions the candidate is most likely to "
          "face. The question bank contains sixty-five questions, each tagged with the "
          "taxonomy skills it assesses, a question kind and a difficulty aligned with "
          "the three experience levels. The composition is shown in Table 3.8."),
        table("Table 3.8: Composition of the interview question bank", [
            ["Area", "Kind", "Questions"],
            ["Programming fundamentals", "Technical and conceptual", "12"],
            ["Frontend and the web", "Technical and conceptual", "10"],
            ["Backend, APIs and databases", "Technical and conceptual", "13"],
            ["Machine learning and data", "Technical and conceptual", "20"],
            ["Projects and behaviour", "Project and behavioural", "10"],
            ["<b>Total</b>", "", "<b>65</b>"],
        ], [0.42, 0.36, 0.22]),
        p("Questions are presented in three groups. The first contains skills the "
          "candidate claims that the role requires, which they should expect to "
          "demonstrate. The second contains requirements the candidate cannot yet "
          "evidence; these are included because such questions are still likely to be "
          "asked, and an honest prepared answer is considerably better than an "
          "improvised one. The third contains project and behavioural questions that "
          "apply to every candidate."),
        h3("3.9.1 Why Retrieval Is Not Used Here"),
        p("It would be natural to assume that this module should also use semantic "
          "retrieval, since the second objective demonstrates that technique. It does "
          "not, and the reason is a matter of engineering judgement rather than "
          "convenience. Semantic retrieval is valuable when a collection is large and "
          "written by others, because embeddings recover relevance that nobody "
          "labelled. The question bank is the opposite: it is small and its tags were "
          "authored as part of this project. Looking up a tag that is known to be "
          "correct is exact, whereas embedding the questions and retrieving them by "
          "similarity would only be approximate."),
        p("Selecting the weaker mechanism because it is the more impressive one would "
          "be poor design. Retrieval nevertheless contributes to this module: the "
          "selected questions are ordered by how strongly the retrieved job "
          "descriptions demanded the skill each question assesses, which is a value "
          "computed by the matching module."),
        h3("3.9.2 Absence of Model Answers"),
        p("Each question states what the interviewer is assessing rather than "
          "supplying a model answer. Authoring sixty-five authoritative answers across "
          "the taxonomy would present a large surface for subtle error, and an "
          "incorrect answer in revision material is worse than no answer at all. "
          "Stating the assessment criterion gives the candidate the information needed "
          "to prepare while leaving the answer to be researched and written in their "
          "own words. A question above the candidate's level is included only when no "
          "easier question exists for that skill, and is explicitly marked as a "
          "stretch question."),

        h2("3.10 Backend Module Structure"),
        p("The backend is organised so that each file has a single responsibility, "
          "which keeps the modules independently testable. The structure is summarised "
          "in Table 3.9."),
        table("Table 3.9: Backend module structure", [
            ["Module", "Responsibility"],
            ["main.py", "FastAPI application, endpoints and the pipeline generator"],
            ["config.py", "Configuration and environment variable loading"],
            ["skills_data.py", "Skill taxonomy and role catalogue"],
            ["experience_levels.py", "Career-stage calibration values"],
            ["resume_parser.py", "PDF and DOCX parsing into structured fields"],
            ["github_analyzer.py", "GitHub REST API access and skill evidence"],
            ["ats_scorer.py", "Deterministic ATS scoring"],
            ["job_matcher.py", "Requirement derivation and match scoring"],
            ["role_recommender.py", "Ranking the candidate across all roles"],
            ["skill_graph.py", "Prerequisite graph and documentation links"],
            ["roadmap.py", "Phased learning plan construction"],
            ["interview_prep.py", "Question selection from the bank"],
            ["summary_builder.py", "Rule-based written summary"],
            ["rag/chunker.py", "Division of job descriptions into chunks"],
            ["rag/embedder.py", "Text to normalised vectors, with offline fallback"],
            ["rag/vector_store.py", "FAISS index and persistence"],
            ["rag/ingest.py", "Index construction and cache invalidation"],
            ["rag/retriever.py", "Query construction and similarity search"],
        ], [0.34, 0.66]),
        pagebreak(),
    ]


# ---------------------------------------------------------------------------
# Chapter 4 — Implementation and Testing
# ---------------------------------------------------------------------------
def chapter_4():
    return [
        chapter("CHAPTER 4", "IMPLEMENTATION AND TESTING"),

        h2("4.1 Languages, IDEs, Tools and Technologies Used"),
        p("The AI-Powered Career Engine is implemented using Python for backend "
          "development and React for frontend development. The project combines "
          "resume parsing, GitHub profile analysis, ATS scoring, retrieval-based job "
          "matching, roadmap construction and interview question selection into a "
          "single application."),

        h3("4.1.1 Programming Languages Used"),
        bold("Python"),
        p("Python is used as the main programming language for backend development. "
          "It is used for resume processing, ATS score calculation, GitHub analysis, "
          "the retrieval pipeline, job matching, roadmap generation and interview "
          "question selection. Python was chosen for the maturity of its text "
          "processing and machine-learning ecosystem."),
        bold("JavaScript"),
        p("JavaScript, in its modern ECMAScript form, is used for frontend "
          "development and for handling interactions between the user interface and "
          "the backend API."),
        bold("IDE Used: Visual Studio Code"),
        p("Visual Studio Code is used for writing, editing, testing and managing the "
          "project code. It provides syntax highlighting, debugging tools, extensions "
          "and an integrated terminal, and supports both the Python backend and the "
          "JavaScript frontend within a single workspace."),

        h3("4.1.2 Tools and Libraries Used"),
        p("The principal libraries used in the backend are listed in Table 4.1. All "
          "of them are open-source and free to use."),
        table("Table 4.1: Python libraries used", [
            ["Library", "Purpose in this project"],
            ["FastAPI", "Backend web framework providing the REST API endpoints and "
                        "automatically generated interactive documentation"],
            ["Uvicorn", "ASGI server used to run the FastAPI application"],
            ["pdfplumber", "Extraction of text from PDF resumes"],
            ["python-docx", "Extraction of text and tables from DOCX resumes"],
            ["requests", "Communication with the GitHub REST API"],
            ["sentence-transformers", "Generation of 384-dimensional sentence "
                                      "embeddings using all-MiniLM-L6-v2"],
            ["faiss-cpu", "Local vector index and exact cosine similarity search"],
            ["scikit-learn", "TF-IDF and Truncated SVD used as the offline embedding "
                             "fallback"],
            ["NumPy", "Vector arithmetic and normalisation"],
            ["python-multipart", "Handling of resume file uploads and form data"],
            ["python-dotenv", "Loading of optional configuration from a local "
                              "environment file"],
        ], [0.26, 0.74]),
        p("On the frontend, React is used to build the user interface as reusable "
          "components, Vite provides the development server and build tooling, and "
          "Tailwind CSS is used for styling. The development server proxies API "
          "requests to the backend so that both halves of the application can be run "
          "locally without cross-origin configuration."),

        h3("4.1.3 Technologies Used"),
        bullet("React-based single-page web interface"),
        bullet("Resume parsing and text extraction from PDF and DOCX"),
        bullet("Rule-based, deterministic ATS scoring"),
        bullet("GitHub REST API integration"),
        bullet("Skill taxonomy with alias and word-boundary matching"),
        bullet("Dense vector embeddings using a locally executed "
               "sentence-transformer"),
        bullet("FAISS vector index with exact cosine similarity search"),
        bullet("Retrieval-Augmented Generation over job-description data"),
        bullet("Weighted skill matching with experience-level calibration"),
        bullet("Prerequisite-graph-based roadmap construction"),
        bullet("REST API development using FastAPI"),
        bullet("Server-Sent Events for genuine pipeline progress reporting"),
        p("It should be noted explicitly that no large language model is used at any "
          "point. The only machine-learning model in the system is the "
          "sentence-transformer used to produce embeddings for retrieval, and that "
          "model is not generative. All scoring, matching, ordering and written output "
          "is produced by deterministic rules."),

        h2("4.2 Testing Techniques"),
        p("Testing is performed to check whether the system works correctly and gives "
          "accurate results. The techniques used in the project are described below."),

        h3("4.2.1 Unit Testing"),
        p("Unit testing is performed by testing each module separately, such as the "
          "resume parser, the GitHub analyser, the ATS scorer, the job matcher, the "
          "roadmap builder and the interview selection module. Each module is given "
          "sample input and its output is checked against the expected result. Unit "
          "tests also verify internal invariants, for example that the ATS component "
          "weights sum to one hundred and that the prerequisite graph contains no "
          "cycles."),

        h3("4.2.2 Integration Testing"),
        p("Integration testing is performed by combining all modules and exercising "
          "the complete workflow. A resume, GitHub profile, target job role and "
          "experience level are supplied as input, and the system is checked to ensure "
          "that data flows correctly from profile analysis through ATS scoring, "
          "retrieval, job matching, role ranking, roadmap construction and interview "
          "selection to the final result."),

        h3("4.2.3 Validation and Property Testing"),
        p("In addition to conventional unit and integration tests, the suite verifies "
          "properties that must hold for every input rather than for one specific "
          "case. Examples include the requirement that the ATS total always equals the "
          "sum of its components, that removing any one resume section changes exactly "
          "one component score, that the roadmap never refers to a blocking skill "
          "absent from the plan, and that identical input always produces identical "
          "output. A structural test also asserts that no backend module imports a "
          "language-model provider, so the claim that none is used is verified "
          "mechanically rather than merely stated."),

        h3("4.2.4 Negative Testing"),
        p("Negative testing supplies deliberately invalid input to confirm that the "
          "system fails safely. Unsupported file types, empty files, files misnamed as "
          "PDFs, scanned documents containing no text layer, unknown GitHub usernames, "
          "exhausted API rate limits and unknown role identifiers are each checked to "
          "confirm that an appropriate status code and a readable message are "
          "returned."),

        h2("4.3 Test Cases Designed"),
        p("A representative selection of the test cases designed for the system is "
          "given in Table 4.2. The complete automated suite contains two hundred and "
          "thirteen checks; Table 4.3 summarises how these are distributed across the "
          "functional areas."),
        table("Table 4.2: Test cases designed", [
            ["ID", "Description", "Input", "Expected output", "Result"],
            ["TC01", "Resume parsing (PDF)", "Valid PDF resume",
             "Resume details and skills extracted correctly", "Pass"],
            ["TC02", "Resume parsing (DOCX)", "Valid DOCX resume",
             "Same skills extracted as from the PDF of the same resume", "Pass"],
            ["TC03", "GitHub analysis", "Valid GitHub username",
             "Profile and repository details retrieved", "Pass"],
            ["TC04", "ATS score generation", "Resume and target role",
             "Score out of 100 with component breakdown", "Pass"],
            ["TC05", "ATS total integrity", "Any resume",
             "Total equals the sum of the nine components", "Pass"],
            ["TC06", "Determinism", "Same resume submitted twice",
             "Identical score and identical wording", "Pass"],
            ["TC07", "Discrimination", "Strong and weak resumes",
             "Weak resume scores substantially lower", "Pass"],
            ["TC08", "No double counting", "Resume with a section removed",
             "Exactly one component score changes", "Pass"],
            ["TC09", "Experience calibration", "Same resume at three levels",
             "Scores decrease as expectation rises", "Pass"],
            ["TC10", "Semantic retrieval", "Query 'PyTorch deep learning'",
             "Relevant job-description passages returned", "Pass"],
            ["TC11", "Role filtering", "Query restricted to a role",
             "Only that role's passages are returned", "Pass"],
            ["TC12", "Skill matching", "Resume skills and role requirements",
             "Matched and missing skills identified with evidence", "Pass"],
            ["TC13", "Role recommendation", "Resume and target role",
             "All six roles ranked by core coverage", "Pass"],
            ["TC14", "Roadmap ordering", "Resume with many gaps",
             "Prerequisites appear before dependent skills", "Pass"],
            ["TC15", "Roadmap closure", "Resume with many gaps",
             "No step blocked by a skill absent from the plan", "Pass"],
            ["TC16", "Interview selection", "Resume and target role",
             "Questions grouped by provable and missing skills", "Pass"],
            ["TC17", "Invalid resume", "Unsupported file type",
             "HTTP 422 with an explanatory message", "Pass"],
            ["TC18", "Invalid GitHub profile", "Unknown username",
             "HTTP 404 with an explanatory message", "Pass"],
            ["TC19", "GitHub failure tolerance", "Unknown username in full pipeline",
             "Analysis completes using resume evidence only", "Pass"],
            ["TC20", "Complete integration", "Resume, GitHub and target role",
             "Complete analysis report produced", "Pass"],
        ], [0.08, 0.20, 0.22, 0.36, 0.14]),
        table("Table 4.3: Automated test coverage by area", [
            ["Functional area", "Checks"],
            ["Backend availability and metadata endpoints", "12"],
            ["Resume parsing, both formats and failure modes", "31"],
            ["GitHub analysis and error handling", "11"],
            ["Retrieval quality and index integrity", "19"],
            ["Experience-level calibration", "24"],
            ["ATS scoring, determinism and discrimination", "22"],
            ["Absence of double counting", "13"],
            ["Job matching and evidence traceability", "14"],
            ["Role recommendation", "11"],
            ["Learning roadmap", "13"],
            ["Interview preparation", "14"],
            ["Complete pipeline, streaming and validation", "20"],
            ["Rule-based summary and absence of a language model", "9"],
            ["<b>Total</b>", "<b>213</b>"],
        ], [0.70, 0.30]),

        h2("4.4 Output Screenshots"),
        figure("fig_4_4_1_login.png", "Fig 4.4.1: Login page", 5.4),
        p("<b>Login Page:</b> Provides registration and sign-in options to access the "
          "Career Engine application. The email entered identifies the session "
          "locally; no password is required and no account server is involved."),
        figure("fig_4_4_2_input.png", "Fig 4.4.2: Input form", 5.4),
        p("<b>Input Form:</b> Allows candidates to upload their resume, enter their "
          "GitHub username, select a target job role and experience level, and provide "
          "the job description they are applying to."),
        figure("fig_4_4_3_overview.png", "Fig 4.4.3: Overview dashboard", 5.4),
        p("<b>Overview Dashboard:</b> Displays the overall ATS score, the job-match "
          "score and a concise summary of the highest-impact improvements available to "
          "the candidate."),
        figure("fig_4_4_4_ats.png", "Fig 4.4.4: ATS score breakdown", 5.4),
        p("<b>ATS Score Breakdown:</b> Shows each of the nine scoring components with "
          "the points earned, the points available, the reason for the score and the "
          "supporting evidence drawn from the resume."),
        figure("fig_4_4_5_jobmatch.png", "Fig 4.4.5: Job match breakdown", 5.4),
        p("<b>Job Match Breakdown:</b> Compares candidate skills with the retrieved "
          "job requirements and displays matched skills, missing skills and the "
          "overall match score with its four components."),
        figure("fig_4_4_6_roadmap.png", "Fig 4.4.6: Learning roadmap", 5.4),
        p("<b>Learning Roadmap:</b> Presents a phased learning plan in which the "
          "missing skills are ordered by the prerequisite graph, with assumed "
          "knowledge surfaced first and each step stating what it unlocks."),
        figure("fig_4_4_7_rolefit.png", "Fig 4.4.7: Role fit analysis", 5.4),
        p("<b>Role Fit Analysis:</b> Compares the candidate's profile with all "
          "supported job roles and ranks them by the share of each role's core "
          "requirements that the candidate can evidence."),
        figure("fig_4_4_8_resume_github.png", "Fig 4.4.8: Resume and GitHub analysis",
               5.4),
        p("<b>Resume and GitHub Analysis:</b> Displays the extracted resume details, "
          "skills, projects, experience and education alongside the evidence derived "
          "from the candidate's public GitHub repositories."),

        h2("4.5 Implementation of Core Modules"),
        h3("4.5.1 Resume Parser"),
        p("The parser reads the uploaded file, normalises the extracted text into "
          "clean lines, segments the document into canonical sections and then "
          "extracts fields from those sections. Two implementation problems are worth "
          "recording. PDF extraction produces the placeholder sequence (cid:127) where "
          "a glyph has no Unicode mapping, typically a bullet character; these were "
          "appearing in the evidence quoted back to the user and are now removed. "
          "Separately, Microsoft Word stores list bullets in the numbering definition "
          "rather than in the paragraph text, so DOCX files initially appeared to "
          "contain no bullets at all and every Word resume scored zero for formatting; "
          "the parser now reconstructs the marker from the paragraph style."),
        h3("4.5.2 GitHub Analyzer"),
        p("The analyser retrieves the public profile and repository list, and derives "
          "skill evidence from repository languages, topics and descriptions. Forked "
          "repositories are excluded, since forking a project is not evidence of "
          "having written it. Failures are mapped to appropriate status codes, and "
          "within the full pipeline a failure is recorded as a warning so that the "
          "analysis completes using resume evidence alone."),
        h3("4.5.3 Pipeline Orchestration"),
        p("The complete analysis is implemented as a Python generator in the "
          "application module. The generator yields a progress event as each stage "
          "begins and ends, and finally yields the result. This single implementation "
          "serves both the conventional JSON endpoint, which drains the generator and "
          "returns the result, and a streaming endpoint that forwards each event to "
          "the browser as a Server-Sent Event. Because the events are emitted by the "
          "stages themselves, the progress displayed in the interface reflects genuine "
          "execution rather than a simulated indicator."),

        h2("4.6 REST API Endpoints"),
        p("The backend exposes the endpoints listed in Table 4.4. Interactive "
          "documentation is generated automatically by FastAPI and is available while "
          "the server is running."),
        table("Table 4.4: REST API endpoints", [
            ["Method", "Endpoint", "Purpose"],
            ["GET", "/api/health", "Service status and vector index statistics"],
            ["GET", "/api/roles", "Supported target roles and their baseline skills"],
            ["GET", "/api/experience-levels", "Career stages and expected coverage"],
            ["GET", "/api/job-descriptions", "The job-description knowledge base"],
            ["GET", "/api/rag/status", "Index size, dimensions and embedding backend"],
            ["GET", "/api/rag/search", "Raw semantic search, for demonstration"],
            ["POST", "/api/rag/reindex", "Rebuild the vector index"],
            ["POST", "/api/parse-resume", "Resume file to structured data"],
            ["POST", "/api/analyze-github", "GitHub username to skill evidence"],
            ["POST", "/api/ats-score", "ATS score and component breakdown"],
            ["POST", "/api/job-match", "Retrieval-based job matching result"],
            ["POST", "/api/recommend-roles", "Ranking across all supported roles"],
            ["POST", "/api/roadmap", "Phased learning plan"],
            ["POST", "/api/interview-prep", "Selected interview questions"],
            ["POST", "/api/analyze", "The complete pipeline in a single call"],
            ["POST", "/api/analyze/stream", "The same pipeline as Server-Sent Events"],
        ], [0.12, 0.34, 0.54]),

        h2("4.7 Results and Observations"),
        p("The complete pipeline executes in approximately three hundred milliseconds "
          "for a typical resume once the vector index has been loaded, which occurs "
          "once at server start. Table 4.5 gives representative stage timings measured "
          "during testing."),
        table("Table 4.5: Observed stage execution times", [
            ["Pipeline stage", "Typical time (ms)"],
            ["Resume parsing", "40 – 70"],
            ["GitHub analysis (when requested)", "400 – 1900"],
            ["Retrieval of job-description evidence", "30 – 80"],
            ["ATS scoring", "5 – 10"],
            ["Job matching", "18 – 25"],
            ["Role recommendation across six roles", "100 – 130"],
            ["Roadmap construction", "under 1"],
            ["Interview question selection", "under 1"],
            ["Summary generation", "under 1"],
        ], [0.62, 0.38]),
        p("GitHub analysis dominates the measured time because it depends on network "
          "requests to an external service. All local computation together accounts "
          "for well under three hundred milliseconds, which confirms that the "
          "deterministic design carries no performance penalty relative to approaches "
          "that call an external model service, and in fact avoids the network latency "
          "such calls would introduce."),
        p("Scoring behaviour was validated against prepared resumes. A strong sample "
          "resume scored in the high eighties to low nineties out of one hundred "
          "against a matching role, while a deliberately weak resume scored six. The "
          "same resume evaluated against different target roles produced clearly "
          "different scores, confirming that the role-specific components respond as "
          "intended. Repeated submission of identical input produced byte-identical "
          "output on every occasion."),
        p("Retrieval quality was examined using queries whose correct answer was "
          "known in advance. The query \"A/B testing and experiment design\" returned "
          "the corresponding data-science requirement at a cosine similarity of 0.87, "
          "and \"PyTorch deep learning models\" returned the matching machine-learning "
          "requirement at 0.85. These values, together with the prefix experiment "
          "described in Section 3.6.5, were used to guide the retrieval design."),
        pagebreak(),
    ]


# ---------------------------------------------------------------------------
# Chapter 5 — Conclusion and Future Scope
# ---------------------------------------------------------------------------
def chapter_5():
    return [
        chapter("CHAPTER 5", "CONCLUSION AND FUTURE SCOPE"),

        h2("5.1 Conclusion"),
        p("The AI-Powered Career Engine was developed to address a problem that "
          "candidates face every time they apply for a technical role: they submit an "
          "application and receive no explanation of how it was judged. Applicant "
          "Tracking Systems filter applications before any human reads them, and the "
          "criteria they apply are not disclosed. A candidate who is rejected learns "
          "nothing that would help the next application. The system developed in this "
          "project makes that evaluation visible."),
        p("The project achieves this through a deliberately transparent design. The "
          "Applicant Tracking System score is produced by nine fixed rules whose "
          "weights sum to one hundred, and every point awarded is accompanied by the "
          "line of the resume that earned it. Job matching is grounded in retrieval: "
          "requirements are drawn from a job-description knowledge base through "
          "semantic search rather than being invented, and the retrieved passage "
          "supporting each requirement can be inspected by the candidate. The learning "
          "roadmap is ordered by an explicit prerequisite graph, so a candidate is "
          "never asked to study a topic before the knowledge it assumes. Interview "
          "questions are selected according to which skills the candidate can and "
          "cannot evidence."),
        p("A consequence of this design worth stating plainly is that the system "
          "contains no large language model. During development the question was "
          "examined directly, and the conclusion was that a generative model would "
          "have added nothing that the system needed while removing the two properties "
          "it most depends upon. A score produced by a language model cannot be "
          "explained in terms of rules, because there are none, and it cannot be "
          "guaranteed to repeat, because the model may answer differently on a second "
          "occasion. Both properties are essential to a tool whose purpose is to tell "
          "a candidate why they were scored as they were. The only model in the system "
          "is the sentence-transformer that converts text into vectors for retrieval, "
          "and that model is not generative: it compares meaning, it does not produce "
          "language. Every sentence shown to the user is assembled from measured "
          "values by rules written for this project."),
        p("The system was validated by an automated suite of two hundred and thirteen "
          "checks covering parsing, scoring, retrieval, matching, roadmap "
          "construction, interview selection and failure handling. The suite verifies "
          "not only that the modules produce correct output on prepared inputs but "
          "also that the stated properties hold: that the score components sum to the "
          "total, that no fact is counted twice, that identical input produces "
          "identical output, that the roadmap is closed under its prerequisites, and "
          "that no backend module imports a language-model provider."),
        p("The three objectives set out in Chapter 1 were met. The system analyses a "
          "resume together with a candidate's public GitHub activity and a target role "
          "to produce an explainable Applicant Tracking System score; it performs "
          "retrieval-augmented job matching over a knowledge base of job descriptions "
          "with traceable evidence; and it generates a prerequisite-ordered learning "
          "roadmap together with a targeted interview preparation set."),

        h2("5.2 Objectives Achieved"),
        table("Table 5.1: Objectives and their outcomes", [
            ["Objective", "Outcome"],
            ["Explainable ATS scoring from resume, GitHub profile and target role",
             "Achieved. Nine deterministic components totalling one hundred points, "
             "each returning the evidence line that produced the score, and each "
             "calibrated to the candidate's declared experience level."],
            ["Retrieval-augmented job matching over job-description data",
             "Achieved. Twelve job descriptions chunked into requirement-level "
             "passages, embedded and indexed in FAISS; requirements retrieved by "
             "semantic search and matched against candidate skills, with the "
             "supporting passage and its similarity score exposed."],
            ["Learning roadmap and interview preparation",
             "Achieved. Missing skills ordered by an eighty-seven-edge prerequisite "
             "graph, closed under prerequisites and grouped into phases; interview "
             "questions selected by skill tag and divided according to which skills "
             "the candidate can evidence."],
        ], [0.34, 0.66]),

        h2("5.3 Limitations of the Present System"),
        p("Several limitations of the present system should be recorded honestly."),
        num("1. The job-description knowledge base contains twelve descriptions across "
            "six roles. This is sufficient to demonstrate that retrieval works and to "
            "produce useful matches for the supported roles, but it is not a "
            "comprehensive representation of the job market."),
        num("2. Skill detection relies on a curated taxonomy of one hundred and twelve "
            "skills with their aliases. A skill that is not present in the taxonomy "
            "will not be detected, however clearly the resume states it."),
        num("3. Resume parsing requires a text layer in the uploaded document. A resume "
            "that has been scanned to an image cannot be read, and the system reports "
            "this condition rather than returning an empty analysis."),
        num("4. GitHub analysis uses the unauthenticated public API by default, which "
            "permits sixty requests per hour from one address. A personal access "
            "token raises this limit substantially but is not required."),
        num("5. The system evaluates evidence of a skill, not depth of competence in "
            "it. A repository that uses a technology and a repository that uses it "
            "well are indistinguishable to the analyser."),
        num("6. The application runs locally and stores no data between sessions. This "
            "is appropriate for a project of this scope and avoids holding personal "
            "data, but it means a candidate cannot track progress over time."),

        h2("5.4 Future Scope"),
        p("The following extensions would build naturally on the present system."),
        num("1. <b>Expansion of the knowledge base.</b> Increasing the number of job "
            "descriptions and the range of roles would improve retrieval coverage "
            "directly. The ingestion pipeline is already automated, so the extension "
            "requires data rather than new code."),
        num("2. <b>Automatic taxonomy growth.</b> Terms that appear frequently in "
            "retrieved requirements but are absent from the taxonomy could be "
            "surfaced for review, allowing the taxonomy to grow in response to the "
            "job market rather than by manual curation alone."),
        num("3. <b>Optical character recognition.</b> Adding an OCR stage would allow "
            "scanned resumes to be analysed, removing the principal category of input "
            "the system currently rejects."),
        num("4. <b>Persistent candidate profiles.</b> Storing analyses against an "
            "authenticated account would allow a candidate to see how their score "
            "changes as they complete roadmap steps, turning a single assessment into "
            "a measurable trajectory."),
        num("5. <b>Broader evidence sources.</b> The GitHub analyser establishes a "
            "pattern for deriving skill evidence from public activity. The same "
            "pattern could be applied to other verifiable sources, such as "
            "competitive-programming profiles or published technical writing."),
        num("6. <b>Assessment of depth.</b> Repository metrics such as commit history, "
            "code volume and test presence could distinguish substantial use of a "
            "technology from incidental use, addressing the limitation recorded in "
            "Section 5.3."),
        num("7. <b>Deployment as a hosted service.</b> The present system runs locally "
            "by design. Hosting it would make it available to candidates generally, "
            "and would require attention to data protection, since resumes contain "
            "personal information."),
        pagebreak(),
    ]


# ---------------------------------------------------------------------------
# References
# ---------------------------------------------------------------------------
def references():
    items = [
        "Reimers, N. and Gurevych, I., “Sentence-BERT: Sentence Embeddings using "
        "Siamese BERT-Networks”, Proceedings of the 2019 Conference on Empirical "
        "Methods in Natural Language Processing, 2019.",
        "Wang, W., Wei, F., Dong, L., Bao, H., Yang, N. and Zhou, M., “MiniLM: "
        "Deep Self-Attention Distillation for Task-Agnostic Compression of "
        "Pre-Trained Transformers”, Advances in Neural Information Processing "
        "Systems, 2020.",
        "Lewis, P., Perez, E., Piktus, A. et al., “Retrieval-Augmented Generation "
        "for Knowledge-Intensive NLP Tasks”, Advances in Neural Information "
        "Processing Systems, 2020.",
        "Johnson, J., Douze, M. and Jégou, H., “Billion-scale similarity "
        "search with GPUs”, IEEE Transactions on Big Data, 2019.",
        "Deerwester, S., Dumais, S. T., Furnas, G. W., Landauer, T. K. and Harshman, "
        "R., “Indexing by Latent Semantic Analysis”, Journal of the American "
        "Society for Information Science, 1990.",
        "Salton, G. and Buckley, C., “Term-weighting approaches in automatic text "
        "retrieval”, Information Processing and Management, 1988.",
        "Pedregosa, F. et al., “Scikit-learn: Machine Learning in Python”, "
        "Journal of Machine Learning Research, volume 12, 2011.",
        "Harris, C. R. et al., “Array programming with NumPy”, Nature, "
        "volume 585, 2020.",
        "Kahn, A. B., “Topological sorting of large networks”, "
        "Communications of the ACM, volume 5, number 11, 1962.",
        "FastAPI Documentation, Ramírez, S., available at "
        "https://fastapi.tiangolo.com",
        "React Documentation, Meta Open Source, available at https://react.dev",
        "Vite Documentation, available at https://vite.dev",
        "Tailwind CSS Documentation, available at https://tailwindcss.com/docs",
        "FAISS Documentation, Meta AI Research, available at "
        "https://faiss.ai",
        "Sentence-Transformers Documentation, available at https://sbert.net",
        "pdfplumber Documentation, available at "
        "https://github.com/jsvine/pdfplumber",
        "python-docx Documentation, available at "
        "https://python-docx.readthedocs.io",
        "GitHub REST API Documentation, available at https://docs.github.com/rest",
        "Hugging Face Model Card, sentence-transformers/all-MiniLM-L6-v2, available "
        "at https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
        "Python Software Foundation, Python Language Reference, version 3.14, "
        "available at https://docs.python.org",
    ]
    blocks = [front("REFERENCES")]
    for i, item in enumerate(items, start=1):
        blocks.append(num("[%d]  %s" % (i, item)))
    return blocks
