# Comprehensive Guide: The Architecture & Mathematics of Transformers

---

## Table of Contents

1. [Mathematical Foundations of Self-Attention](#1-mathematical-foundations-of-self-attention)
2. [End-to-End Walkthrough of a Transformer Layer](#2-end-to-end-walkthrough-of-a-transformer-layer)
3. [High-Level Plain-English Intuition](#3-high-level-plain-english-intuition)
4. [Single Transformer Layer Visual](#4-single-transformer-layer-visual)
5. [Weight-by-Weight Visual Walkthrough](#5-weight-by-weight-visual-walkthrough)

---

## 1. Mathematical Foundations of Self-Attention

Self-Attention allows a model to calculate the contextual relevance of words in a sequence using **Query** ($\mathbf{Q}$), **Key** ($\mathbf{K}$), and **Value** ($\mathbf{V}$) representations.

### Master Formula

$$\text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{Softmax}\left(\frac{\mathbf{Q}\mathbf{K}^T}{\sqrt{d_k}}\right)\mathbf{V}$$

Throughout this section we trace the sequence **"I like tea"** with 2-dimensional vectors ($d_k = 2$), computing attention for the query token **"tea"**.

---

### Step 1: Matrix Multiplication for Raw Scores ($\mathbf{Q}\mathbf{K}^T$)

Multiplying a $(1 \times 2)$ Query vector by a $(2 \times 3)$ Key matrix yields a $(1 \times 3)$ row matrix containing all three dot products at once.

**Query vector ($\mathbf{Q}$):**

$$\mathbf{Q} = \begin{bmatrix} 1 & 1 \end{bmatrix} \quad (1 \times 2)$$

**Key matrix ($\mathbf{K}$):**

$$\mathbf{K}_{\text{I}} = \begin{bmatrix} 1 \\ 0 \end{bmatrix}, \quad \mathbf{K}_{\text{like}} = \begin{bmatrix} 0 \\ 1 \end{bmatrix}, \quad \mathbf{K}_{\text{tea}} = \begin{bmatrix} 1 \\ 1 \end{bmatrix} \implies \mathbf{K} = \begin{bmatrix} 1 & 0 & 1 \\ 0 & 1 & 1 \end{bmatrix} \quad (2 \times 3)$$

**Multiplication:**

$$\mathbf{Q} \mathbf{K}^T = \begin{bmatrix} 1 & 1 \end{bmatrix} \begin{bmatrix} 1 & 0 & 1 \\ 0 & 1 & 1 \end{bmatrix}$$

| Entry | Token | Computation | Result |
|:-----:|:-----:|:-----------:|:------:|
| 1st | "I" | $(1 \cdot 1) + (1 \cdot 0)$ | $1$ |
| 2nd | "like" | $(1 \cdot 0) + (1 \cdot 1)$ | $1$ |
| 3rd | "tea" | $(1 \cdot 1) + (1 \cdot 1)$ | $2$ |

$$\text{Raw Scores Vector} = \begin{bmatrix} 1 & 1 & 2 \end{bmatrix}$$

---

### Step 2: Scaling Step ($\frac{\mathbf{Q}\mathbf{K}^T}{\sqrt{d_k}}$)

Scale raw scores by $\sqrt{d_k} = \sqrt{2} \approx 1.414$ to keep numerical values stable:

$$\text{Scaled Scores} = \begin{bmatrix} \frac{1}{1.414} & \frac{1}{1.414} & \frac{2}{1.414} \end{bmatrix} \approx \begin{bmatrix} 0.707 & 0.707 & 1.414 \end{bmatrix}$$

> **Why scale?** Without scaling, dot products grow with dimension $d_k$, pushing Softmax into regions with vanishingly small gradients. Dividing by $\sqrt{d_k}$ keeps the variance of the scores at roughly $1$.

---

### Step 3: Softmax Probability Normalization

Softmax exponentiates each value ($e^{x_i}$) so all numbers become positive, then divides each by the sum of all exponentiated values ($\sum e^{x_j}$) to produce probabilities that sum to $1.0$ ($100\%$).

$$\text{Softmax}(x_i) = \frac{e^{x_i}}{\sum_j e^{x_j}}$$

#### 3.1 Calculate Exponentials ($e^{x_i}$)

| Token | $x_i$ | $e^{x_i}$ |
|:-----:|:-----:|:---------:|
| "I" | $0.707$ | $\approx 2.028$ |
| "like" | $0.707$ | $\approx 2.028$ |
| "tea" | $1.414$ | $\approx 4.112$ |

#### 3.2 Sum Exponentials ($\sum e^{x_j}$)

$$\sum e^{x_j} = 2.028 + 2.028 + 4.112 = 8.168$$

#### 3.3 Compute Probabilities

| Token | Computation | Probability | Percentage |
|:-----:|:-----------:|:-----------:|:----------:|
| "I" | $\frac{2.028}{8.168}$ | $\approx 0.2483$ | **24.83%** |
| "like" | $\frac{2.028}{8.168}$ | $\approx 0.2483$ | **24.83%** |
| "tea" | $\frac{4.112}{8.168}$ | $\approx 0.5034$ | **50.34%** |

$$\text{Softmax}([0.707,\ 0.707,\ 1.414]) \approx \begin{bmatrix} 0.248 & 0.248 & 0.504 \end{bmatrix}$$

---

### Step 4: Mix Value Vectors ($\text{Softmax} \times \mathbf{V}$)

Multiply the $(1 \times 3)$ Softmax probability vector by the $(3 \times 2)$ Value matrix ($\mathbf{V}$) to compute the weighted contextual sum.

**Value matrix ($\mathbf{V}$):**

$$\mathbf{V}_{\text{I}} = [1, 0], \quad \mathbf{V}_{\text{like}} = [0, 1], \quad \mathbf{V}_{\text{tea}} = [1, 1] \implies \mathbf{V} = \begin{bmatrix} 1 & 0 \\ 0 & 1 \\ 1 & 1 \end{bmatrix}$$

#### 4.1 Multiply Value Vectors by Weights

| Token | Weight | Computation | Weighted Vector |
|:-----:|:------:|:-----------:|:---------------:|
| "I" | $24.8\%$ | $0.248 \times [1, 0]$ | $[0.248,\ 0.000]$ |
| "like" | $24.8\%$ | $0.248 \times [0, 1]$ | $[0.000,\ 0.248]$ |
| "tea" | $50.3\%$ | $0.503 \times [1, 1]$ | $[0.503,\ 0.503]$ |

#### 4.2 Sum Weighted Components

- **First dimension ($x$-axis):** $0.248 + 0.000 + 0.503 = 0.751 \approx \mathbf{0.75}$
- **Second dimension ($y$-axis):** $0.000 + 0.248 + 0.503 = 0.751 \approx \mathbf{0.75}$

$$\text{Attention Output} = \begin{bmatrix} 0.248 & 0.248 & 0.503 \end{bmatrix} \begin{bmatrix} 1 & 0 \\ 0 & 1 \\ 1 & 1 \end{bmatrix} = \begin{bmatrix} 0.751 & 0.751 \end{bmatrix} \approx \mathbf{[0.75,\ 0.75]}$$

---

## 2. End-to-End Walkthrough of a Transformer Layer

Mathematical trace of token `"tea"` passing through **Layer 1** of a Transformer.

```text
[Input Token Embedding] ──> [Self-Attention] ──> [Residual 1] ──> [LayerNorm 1]
        ──> [MLP / FFN] ──> [Residual 2] ──> [LayerNorm 2] ──> [Output]
```

### Initial State

| Quantity | Symbol | Value |
|:---------|:------:|:-----:|
| Token Input Vector | $\mathbf{x}_{\text{tea}}$ | $[1.0,\ 2.0]$ |
| Self-Attention Output | $\mathbf{a}_{\text{tea}}$ | $[0.75,\ 0.75]$ |

---

### Step 1: Look Around (Q/K/V Attention)

$$\mathbf{a}_{\text{tea}} = \text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = [0.75,\ 0.75]$$

---

### Step 2: Residual Connection 1 (Add)

Add the original input embedding directly to the attention output:

$$\mathbf{x}_{\text{res1}} = \mathbf{x}_{\text{tea}} + \mathbf{a}_{\text{tea}} = [1.0,\ 2.0] + [0.75,\ 0.75] = [1.75,\ 2.75]$$

---

### Step 3: Normalization 1 (LayerNorm)

Center numbers to mean $\mu = 0$ and scale variance to $\sigma^2 = 1$.

1. **Mean ($\mu$):**
    $$\mu = \frac{1.75 + 2.75}{2} = 2.25$$

2. **Variance ($\sigma^2$):**
    $$\sigma^2 = \frac{(1.75 - 2.25)^2 + (2.75 - 2.25)^2}{2} = \frac{0.25 + 0.25}{2} = 0.25$$

3. **Standard Deviation ($\sigma$):**
    $$\sigma = \sqrt{0.25} = 0.5$$

4. **Normalize** $\left(\frac{x_i - \mu}{\sigma}\right)$:

    - First element: $\frac{1.75 - 2.25}{0.5} = \mathbf{-1.0}$
    - Second element: $\frac{2.75 - 2.25}{0.5} = \mathbf{1.0}$

$$\mathbf{x}_{\text{norm1}} = [-1.0,\ 1.0]$$

---

### Step 4: Feed-Forward Network / MLP

Process the token independently using weight matrix $\mathbf{W}_{\text{mlp}} = \begin{bmatrix} 2 & 0 \\ 1 & 1 \end{bmatrix}$ and ReLU activation ($\max(0, x)$).

1. **Linear Transformation:**
    $$[-1.0,\ 1.0] \begin{bmatrix} 2 & 0 \\ 1 & 1 \end{bmatrix} = [(-1.0)(2) + (1.0)(1),\ (-1.0)(0) + (1.0)(1)] = [-1.0,\ 1.0]$$

2. **ReLU Activation:**
    $$\mathbf{m}_{\text{mlp}} = \text{ReLU}([-1.0,\ 1.0]) = [0.0,\ 1.0]$$

---

### Step 5: Residual Connection 2 (Add)

Add the normalized input state ($\mathbf{x}_{\text{norm1}}$) to the MLP output ($\mathbf{m}_{\text{mlp}}$):

$$\mathbf{x}_{\text{res2}} = \mathbf{x}_{\text{norm1}} + \mathbf{m}_{\text{mlp}} = [-1.0,\ 1.0] + [0.0,\ 1.0] = [-1.0,\ 2.0]$$

---

### Step 6: Normalization 2 (LayerNorm)

1. **Mean ($\mu$):**
    $$\mu = \frac{-1.0 + 2.0}{2} = 0.5$$

2. **Variance ($\sigma^2$):**
    $$\sigma^2 = \frac{(-1.0 - 0.5)^2 + (2.0 - 0.5)^2}{2} = \frac{2.25 + 2.25}{2} = 2.25$$

3. **Standard Deviation ($\sigma$):**
    $$\sigma = \sqrt{2.25} = 1.5$$

4. **Normalize:**

    - First element: $\frac{-1.0 - 0.5}{1.5} = \mathbf{-1.0}$
    - Second element: $\frac{2.0 - 0.5}{1.5} = \mathbf{1.0}$

$$\mathbf{x}_{\text{out}} = [-1.0,\ 1.0]$$

---

### Layer 1 Flow Summary

| Stage | Operation | Vector |
|:-----:|:----------|:------:|
| 0 | Input $\mathbf{x}$ | $[1.0,\ 2.0]$ |
| 1 | Attention Output $\mathbf{a}$ | $[0.75,\ 0.75]$ |
| 2 | Residual 1 $(\mathbf{x} + \mathbf{a})$ | $[1.75,\ 2.75]$ |
| 3 | LayerNorm 1 | $[-1.0,\ 1.0]$ |
| 4 | MLP / Feed-Forward | $[0.0,\ 1.0]$ |
| 5 | Residual 2 $(\text{Norm1} + \text{MLP})$ | $[-1.0,\ 2.0]$ |
| 6 | **Layer 1 Output (Input to Layer 2)** | $\mathbf{[-1.0,\ 1.0]}$ |

$$\begin{aligned}
\text{Input } \mathbf{x} &= [1.0,\ 2.0] \\
\downarrow \\
\text{Attention Output } \mathbf{a} &= [0.75,\ 0.75] \\
\downarrow \\
\text{Residual 1 } (\mathbf{x} + \mathbf{a}) &= [1.75,\ 2.75] \\
\downarrow \\
\text{LayerNorm 1} &= [-1.0,\ 1.0] \\
\downarrow \\
\text{MLP / Feed-Forward} &= [0.0,\ 1.0] \\
\downarrow \\
\text{Residual 2 } (\text{Norm1} + \text{MLP}) &= [-1.0,\ 2.0] \\
\downarrow \\
\mathbf{\text{Layer 1 Output (Input to Layer 2)}} &= \mathbf{[-1.0,\ 1.0]}
\end{aligned}$$

---

## 3. High-Level Plain-English Intuition

### What Is the Model Trying to Do?

Imagine you are writing a story one word at a time. Every time you pick the next word, you need to read what you've written so far so the new word makes sense in context.

A Transformer model does the exact same thing, moving through **4 main stages** for every single word it generates.

### Stage 1: Look Around (Attention & Softmax)

- **The Goal:** Figure out which previous words matter right now.
- **In Everyday Terms:** When writing the word "tea" in the phrase "I like tea", the model looks back at "I" and "like".
- **How It Works:** It compares "tea" against every word, gets raw connection scores, converts them into percentages ($25\%$ "I", $25\%$ "like", $50\%$ "tea"), and mixes their meaning together. Now "tea" isn't just an isolated word in a dictionary — it's a beverage that *you like*.

### Stage 2: Keep the Original Meaning (Residual Connections)

- **The Goal:** Make sure the model doesn't "forget" the original word while mixing in context.
- **In Everyday Terms:** You add the newly blended context back onto the original starting word. It's like adding spices to a dish: you want the flavor of the spices, but you don't want to completely lose the base ingredient.

### Stage 3: Tidy the Numbers (Layer Normalization)

- **The Goal:** Keep the math under control.
- **In Everyday Terms:** As numbers pass through dozens of calculation layers, they can quickly grow out of control or shrink to zero. Normalization resets the scale to a neat average (mean of $0$, variance of $1$) so the next layer can process the information cleanly without crashing or glitching.

### Stage 4: Think & Refine (Feed-Forward Network / MLP)

- **The Goal:** Perform deep reasoning on the contextualized word.
- **In Everyday Terms:** After looking at other words, the model uses its internal "knowledge bank" (learned memory) to think about what this combined meaning actually implies before passing the thought up to the next layer.

### Why Do We Repeat This in Layers?

| Depth | What It Learns |
|:------|:---------------|
| **Layer 1** | Basic grammar and immediate word pairings |
| **Middle Layers** | Topic, tone, and deeper context |
| **Final Layer** | The exact best word to predict next |

### What Does MLP Mean?

**MLP** stands for **Multi-Layer Perceptron**.

In simple terms, an MLP is a basic type of artificial neural network (or "feed-forward" network). It acts as the model's internal knowledge bank and processing center.

- **What it consists of:** Layers of artificial "neurons" connected by mathematical weights, followed by non-linear activation functions (like ReLU or GELU).
- **Its role alongside Attention:**
  - While **Self-Attention** helps words look around and gather context from other words,
  - The **MLP** processes each word individually to refine its meaning, pull from learned facts/knowledge, and prepare the representation for the next layer.

---

## 4. Single Transformer Layer Visual

Data flows **bottom to top**. Residual connections carry the earlier state forward and add the sub-layer output to it.

```text
       ┌───────────────────────────────────────────┐
       │             LAYER 1 OUTPUT                │
       └─────────────────────┬─────────────────────┘
                             │
                             ▼
 ┌───────────────────────────────────────────────────────┐  ▲
 │  [Step 6]      LAYER NORMALIZATION 2                  │  │
 │                Tidy numbers (Mean=0, Var=1)           │  │
 └───────────────────────────┬───────────────────────────┘  │
                             │                              │
 ┌───────────────────────────┴───────────────────────────┐  │
 │  [Step 5]         RESIDUAL CONNECTION 2               │  │
 │              ( Norm 1 Output  +  MLP Output )         │  │
 └─────────────┬───────────────────────────▲─────────────┘  │
               │                           │                │
               │   ┌───────────────────────┴───────────┐    │
               │   │ [Step 4]      MLP / FFN           │    │
               │   │       (Feed-Forward Network)      │    │
               │   │      "Think & refine meaning      │    │
               │   │       using learned memory"       │    │
               │   └───────────────────────▲───────────┘    │
               │                           │                │
 ┌─────────────▼───────────────────────────┴─────────────┐  │   FLOW
 │  [Step 3]      LAYER NORMALIZATION 1                  │  │    OF
 │                Tidy numbers (Mean=0, Var=1)           │  │   DATA
 └───────────────────────────┬───────────────────────────┘  │
                             │                              │
 ┌───────────────────────────┴───────────────────────────┐  │
 │  [Step 2]         RESIDUAL CONNECTION 1               │  │
 │               ( Input Token  +  Attention )           │  │
 └─────────────┬───────────────────────────▲─────────────┘  │
               │                           │                │
               │   ┌───────────────────────┴───────────┐    │
               │   │ [Step 1]  MULTI-HEAD ATTENTION    │    │
               │   │            (Q × K × V)            │    │
               │   │      "Look around at context"     │    │
               │   └───────────────────────▲───────────┘    │
               │                           │                │
 ┌─────────────▼───────────────────────────┴─────────────┐  │
 │  [Step 0]               INPUT                         │  │
 │                  Token Embedding Vector               │  │
 └───────────────────────────────────────────────────────┘  │
```

---

## 5. Weight-by-Weight Visual Walkthrough

A simple, visual guide to how the Transformer processes the phrase **"I like tea"** using each set of learned weights — from the attention projections all the way to picking the next word.

> **Note:** This section uses its own small toy weight matrices ($W_Q$, $W_K$, $W_V$, $W_{\text{mlp}}$, $W_{\text{out}}$), so a few intermediate numbers differ slightly from Section 1 (for example, the Key for "tea" here is $[2, 1]$ rather than $[1, 1]$). The mechanics are identical.

### The Setup

We convert our words into simplified 2-number vectors:

| Token | Embedding |
|:-----:|:---------:|
| "I" | $[1, 0]$ |
| "like" | $[0, 1]$ |
| "tea" | $[1, 1]$ |

When predicting what comes next, the model focuses on the **last token**, "tea" ($\mathbf{x} = [1, 1]$).

---

### 5.1 Attention Weights ($W_Q, W_K, W_V$)

**Role:** Turn raw words into a **Query** (what am I looking for?), a **Key** (what am I?), and a **Value** (what information do I hold?).

```text
                  Current Word: "tea" [1, 1]
                     /          |          \
                    /           |           \
          × W_Q [1 0]     × W_K [1 0]     × W_V [0 1]
                [0 1]           [1 1]           [1 0]
                 │              │              │
                 ▼              ▼              ▼
              Query          Key            Value
              [1, 1]         [2, 1]         [1, 1]
```

**Calculation for "tea":**

1. **Query ($\mathbf{Q}$):**
    $$[1, 1] \begin{bmatrix} 1 & 0 \\ 0 & 1 \end{bmatrix} = [(1\cdot1 + 1\cdot0),\ (1\cdot0 + 1\cdot1)] = \mathbf{[1, 1]}$$

2. **Key ($\mathbf{K}$):**
    $$[1, 1] \begin{bmatrix} 1 & 0 \\ 1 & 1 \end{bmatrix} = [(1\cdot1 + 1\cdot1),\ (1\cdot0 + 1\cdot1)] = \mathbf{[2, 1]}$$

3. **Value ($\mathbf{V}$):**
    $$[1, 1] \begin{bmatrix} 0 & 1 \\ 1 & 0 \end{bmatrix} = [(1\cdot0 + 1\cdot1),\ (1\cdot1 + 1\cdot0)] = \mathbf{[1, 1]}$$

---

### 5.2 Mix Context (Self-Attention Outcome)

**Role:** Compare the Query of "tea" against the Keys of all previous words ("I", "like", "tea") to create percentage attention scores.

```text
  "tea" Query [1, 1]  ──> Compares against  ──>  "I"    Key [1, 0] = Score 1  (25%)
                                            ──>  "like" Key [0, 1] = Score 1  (25%)
                                            ──>  "tea"  Key [2, 1] = Score 3  (50%)
                                                            │
                                                            ▼
                                                Blended Value Result:
                                                 Attention Output = [0.75, 0.75]
```

| Compared Token | Key | Score ($\mathbf{Q} \cdot \mathbf{K}$) | Attention |
|:--------------:|:---:|:-------------------------------------:|:---------:|
| "I" | $[1, 0]$ | $1$ | $25\%$ |
| "like" | $[0, 1]$ | $1$ | $25\%$ |
| "tea" | $[2, 1]$ | $3$ | $50\%$ |

The weighted blend of the Value vectors gives the **Attention Output** $= [0.75,\ 0.75]$, which is added back to the original embedding (residual connection) to give the raw blended numbers used in the next step.

---

### 5.3 Normalization Weights ($\gamma, \beta$)

**Role:** Take the blended numbers and stabilize them so they don't explode or shrink to zero.

```text
                  Raw Blended Numbers [ 1.75, 2.75 ]
                               │
                               ▼
                   Calculate Average (Mean = 2.25)
                   Calculate Spread  (Std  = 0.5)
                               │
                               ▼
                    Subtract Mean & Divide Std
                               │
                               ▼
                   Normalized Result [ -1.0, 1.0 ]
```

**Calculation:**

1. **Mean ($\mu$):**
    $$\mu = \frac{1.75 + 2.75}{2} = 2.25$$

2. **Standard Deviation ($\sigma$):**
    $$\sigma = \sqrt{\frac{(1.75 - 2.25)^2 + (2.75 - 2.25)^2}{2}} = 0.5$$

3. **Normalized Output:**

    - Element 1: $\frac{1.75 - 2.25}{0.5} = \mathbf{-1.0}$
    - Element 2: $\frac{2.75 - 2.25}{0.5} = \mathbf{1.0}$

$$\text{Normalized Output} = \mathbf{[-1.0,\ 1.0]}$$

> In a real model, LayerNorm then applies a learned scale $\gamma$ and shift $\beta$: $\hat{x}_i \cdot \gamma + \beta$. Here we use $\gamma = 1$, $\beta = 0$, so the output is unchanged.

---

### 5.4 MLP Weights ($W_{\text{mlp}}$)

**Role:** Process the contextualized word through the model's internal memory bank to think about what "tea you like" actually means.

```text
                 Normalized Input [ -1.0, 1.0 ]
                           │
                           ▼
                   Linear Projection
                  × W_mlp [ 2  0 ]
                          [ 1  1 ]
                           │
                           ▼
                  Linear Result [ -1.0, 1.0 ]
                           │
                           ▼
                  Activation (ReLU)
                      max(0, x)
                           │
                           ▼
                  Processed Output [ 0.0, 1.0 ]
```

**Calculation:**

1. **Multiply by MLP Weights:**
    $$[-1.0,\ 1.0] \begin{bmatrix} 2 & 0 \\ 1 & 1 \end{bmatrix} = [(-1.0\cdot2 + 1.0\cdot1),\ (-1.0\cdot0 + 1.0\cdot1)] = \mathbf{[-1.0,\ 1.0]}$$

2. **Apply Activation Function** ($\text{ReLU} = \max(0, x)$):
    $$\text{Output} = [\max(0, -1.0),\ \max(0, 1.0)] = \mathbf{[0.0,\ 1.0]}$$

---

### 5.5 Output Weights / Vocabulary Head ($W_{\text{out}}$)

**Role:** Take the final thought vector and multiply it across the vocabulary matrix to pick the next word.

```text
                    Final Thought Vector [ 0.0, 1.0 ]
                                   │
                                   ▼
                       × Output Matrix W_out
                          [ -1.0   2.0 ]  <-- "and"
                          [  3.0   0.5 ]  <-- "everyday"
                                   │
                                   ▼
                       Raw Scores (Logits)
                         "and"      = 3.0
                         "everyday" = 0.5
                                   │
                                   ▼
                       Softmax (Percentages)
                         "and"      = 92.4%
                         "everyday" =  7.6%
```

**Calculation:**

1. **Multiply Thought Vector by Word Columns:**

    - Score for "and": $(0.0 \cdot -1.0) + (1.0 \cdot 3.0) = \mathbf{3.0}$
    - Score for "everyday": $(0.0 \cdot 2.0) + (1.0 \cdot 0.5) = \mathbf{0.5}$

2. **Convert to Percentages (Softmax):**

| Candidate | Logit | $e^{\text{logit}}$ | Probability | Percentage |
|:---------:|:-----:|:------------------:|:-----------:|:----------:|
| "and" | $3.0$ | $\approx 20.085$ | $\frac{20.085}{21.733} \approx 0.924$ | **92.4%** |
| "everyday" | $0.5$ | $\approx 1.648$ | $\frac{1.648}{21.733} \approx 0.076$ | **7.6%** |

$$\text{Total Sum} = 20.085 + 1.648 = 21.733$$

**Predicted Next Word: "and"** — producing *"I like tea and…"*

---

### Weight Summary

| Weight Set | Symbol | What It Does | Input → Output (for "tea") |
|:-----------|:------:|:-------------|:---------------------------|
| Attention projections | $W_Q, W_K, W_V$ | Build Query / Key / Value | $[1, 1]$ → $\mathbf{Q}=[1,1],\ \mathbf{K}=[2,1],\ \mathbf{V}=[1,1]$ |
| Attention mixing | — | Blend Values by attention scores | Scores $[1, 1, 3]$ → $[0.75, 0.75]$ |
| LayerNorm | $\gamma, \beta$ | Stabilize scale | $[1.75, 2.75]$ → $[-1.0, 1.0]$ |
| Feed-forward | $W_{\text{mlp}}$ | Refine meaning | $[-1.0, 1.0]$ → $[0.0, 1.0]$ |
| Vocabulary head | $W_{\text{out}}$ | Score every next word | $[0.0, 1.0]$ → "and" $92.4\%$ |

---

## Quick Reference

| Component | Formula | Purpose |
|:----------|:--------|:--------|
| Scaled Dot-Product Attention | $\text{Softmax}\left(\frac{\mathbf{Q}\mathbf{K}^T}{\sqrt{d_k}}\right)\mathbf{V}$ | Gather context from other tokens |
| Softmax | $\frac{e^{x_i}}{\sum_j e^{x_j}}$ | Turn scores into probabilities |
| Residual Connection | $\mathbf{x} + f(\mathbf{x})$ | Preserve original signal |
| Layer Normalization | $\frac{x_i - \mu}{\sigma}$ | Stabilize scale of activations |
| Feed-Forward / MLP | $\text{ReLU}(\mathbf{x}\mathbf{W}_1)\mathbf{W}_2$ | Per-token refinement using learned knowledge |
