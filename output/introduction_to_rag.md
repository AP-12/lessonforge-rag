# Introduction to RAG

## What is RAG?

RAG means **Retrieval-Augmented Generation**. It is a way to help an AI language model answer a question using useful information that is found first.

Think of an open-book exam. You ask a question, find the right page in a book, and use that page to write an answer. RAG follows a similar idea: it searches a collection of information, gives the useful parts to the AI model, and asks the model to answer using them.

The search step does not teach or retrain the model. It finds information for the current question and places it beside that question.

## Why use RAG?

A language model is an AI program that learns patterns from examples during training. Its training may not include a company's latest rules, a new product guide, or your own class notes. RAG can search those materials when a question arrives. This can make an answer more relevant to the information you provide and easier to check.

RAG does not guarantee that an answer is true. The search might find the wrong page, or the model might misunderstand a useful page. People still need to check important answers.

## How does RAG work?

1. **Collect information.** A system stores useful files, such as guides or articles, in a searchable collection.
2. **Ask a question.** The learner types a question.
3. **Retrieve useful parts.** The system searches the collection for sections related to the question. This search is called *retrieval*.
4. **Add the parts as context.** The system gives the question and the found sections to the language model. *Context* means the information available to the model for this answer.
5. **Generate an answer.** The model writes a response using the question and context. *Generate* means create new text.

## Example

Imagine a college has a guide that says, “Students may borrow a laptop for up to seven days. Ask the library desk to renew it.” A student asks: **“How long can I borrow a laptop?”**

The RAG system searches the college guide and finds that sentence. It gives the sentence and the student's question to the model. The model can answer: “You can borrow a laptop for up to seven days.” The answer is based on the guide that was found.

If the search finds an old guide with a different rule, the answer could still be wrong. The guide's date and the source of the answer matter.

## Recap

- RAG searches for information before an AI model answers.
- It gives the question and useful found information to the model as context.
- It can help answer questions about information that was not part of the model's training.
- It does not retrain the model or guarantee a correct answer.

In short: **search first, then answer with the useful information.**
