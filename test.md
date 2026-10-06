# Heading 1

## Heading 2

### Heading 3

#### Heading 4

##### Heading 5

###### Heading 6

# A very long H1 title that likely exceeds many viewport widths so we can verify the underline matches the title length even when the title is not short

## H2 with **bold**, *italic*, `code`, [a link](https://example.com) inline

---

## Paragraphs and inline formatting

A plain paragraph with no formatting.

A paragraph with **bold**, *italic with asterisks*, _italic with underscores_, ~~strikethrough~~, `inline code`, and [a link to example.com](https://example.com). All on one line.

Nested formatting: **bold with *italic inside* and back to bold**, and *italic with **bold inside** and back to italic*. Also **_bold italic_** and `code with *no formatting* inside because it is code`.

Adjacent links separated by slashes: [Scryfall](https://scryfall.com) / [NetrunnerDB](https://netrunnerdb.com) / [RingsDB](https://ringsdb.com) — the `/` should not be colored like a link.

Word boundary check: this_is_snake_case should NOT render as italic. Neither should 2*x or a*b when they are not paired emphasis.

A very long paragraph that will definitely wrap across the viewport width. It contains a long stream of words without any special formatting so we can see how the word-wrap distributes content. The wrap should break at word boundaries and preserve leading indentation conventions, which is to say none for plain paragraphs. It should re-flow when the pane is resized.

A long paragraph with **some bold text that is long enough that it might straddle a wrap boundary and we should see the bold styling continue on both visual lines** and also *a long italic stretch that similarly spans multiple visual lines after wrapping*.

---

## Task lists

- [ ] A simple open task
- [x] A completed task
- [X] Also completed (uppercase X)
- [ ] A task with **bold** and *italic* and `code` and [a link](https://example.com)
- [ ] A very long task description that should wrap across multiple visual lines and have the continuation aligned under the text rather than repeating the task box on continuation lines
  - [ ] A nested open task
  - [x] A nested completed task
    - [ ] A deeper nested task with its own long description that also needs to wrap to verify indentation is preserved across nesting levels

Plain bullet list (not a task list):

- Just a bullet
- Another bullet
- Bullet with **bold** and a [link](https://example.com)

---

## Blockquotes

> A simple single-line blockquote.

> A multi-paragraph blockquote with **bold** and *italic* text.
> Continuation line stays inside the blockquote marker.

> A very long blockquote line that should wrap across multiple visual lines, with each continuation line preserving the ▌ marker so the reader can see the quote stretches across multiple lines even after wrapping.

> > Nested blockquote: two levels deep.
> > > Even deeper: three levels.

---

## Horizontal rules

Above this is a `---` HR:

---

Above this is `***`:

***

And `___`:

___

HRs should span the full viewport width and re-flow on resize.

---

## Tables

Simple table, short content:

| Col 1 | Col 2 | Col 3 |
| ----- | ----- | ----- |
| a     | b     | c     |
| d     | e     | f     |

Table with alignments:

| Left     | Center   | Right    |
| :------- | :------: | -------: |
| foo      | bar      | baz      |
| short    | wide content | 1   |
| 1        | 2        | 3        |

Table with inline formatting in cells:

| #   | Name           | Notes                                                           |
| --- | -------------- | --------------------------------------------------------------- |
| 1   | **Bold name**  | Has *italic* and `code` and a [link](https://example.com).      |
| 2   | `code_id`      | Contains ~~strikethrough~~ content.                             |
| 3   | *Italic entry* | **Nested *formatting*** inside a cell.                          |

Wide table forcing cells to wrap:

| Phase | Scope                                                                                         | Notes                                                                         |
| ----- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 1     | **MVP — card viewer**: Scryfall-style single-card detail page with filterable search          | Lean on existing indexed editions/oracle_cards schema; defer deckbuilder      |
| 2     | **Users + deckbuilder**: account system, deck CRUD, legality validation per format            | Blocked on deciding auth provider; see ADR-0003                               |
| 3     | **Online 1v1 gameplay**: real-time matchmaking, deterministic game state, spectator mode      | Network layer TBD; WebRTC vs server-authoritative under discussion            |

---

## Fenced code blocks

### Python

```python
import sys
from typing import Iterable

def greet(name: str, times: int = 1) -> None:
    """A docstring that spans
    multiple lines."""
    for i in range(times):
        print(f"Hello, {name}!")

if __name__ == "__main__":
    greet("world", times=3)
```

### JavaScript

```javascript
const greet = (name, times = 1) => {
    for (let i = 0; i < times; i++) {
        console.log(`Hello, ${name}!`);
    }
};

greet("world", 3);
```

### TypeScript

```typescript
interface User {
    id: number;
    name: string;
}

const users: User[] = [
    { id: 1, name: "alice" },
    { id: 2, name: "bob" },
];
```

### Rust

```rust
fn main() {
    let numbers = vec![1, 2, 3, 4, 5];
    let sum: i32 = numbers.iter().sum();
    println!("Sum = {}", sum);
}
```

### Go

```go
package main

import "fmt"

func main() {
    for i := 0; i < 3; i++ {
        fmt.Println("hello", i)
    }
}
```

### C

```c
#include <stdio.h>

int main(void) {
    printf("Hello, world\n");
    return 0;
}
```

### C++

```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<int> v = {1, 2, 3};
    for (int x : v) std::cout << x << '\n';
}
```

### Ruby

```ruby
def greet(name, times: 1)
  times.times { puts "Hello, #{name}!" }
end

greet("world", times: 3)
```

### Java

```java
public class Hello {
    public static void main(String[] args) {
        for (int i = 0; i < 3; i++) {
            System.out.println("hello " + i);
        }
    }
}
```

### PHP

```php
<?php
function greet($name, $times = 1) {
    for ($i = 0; $i < $times; $i++) {
        echo "Hello, $name!\n";
    }
}

greet("world", 3);
```

### Shell

```bash
#!/usr/bin/env bash
set -euo pipefail

for f in *.md; do
    echo "Processing $f"
    wc -l "$f"
done
```

### HTML

```html
<!DOCTYPE html>
<html>
<head><title>Hello</title></head>
<body>
    <h1>Hello, <em>world</em>!</h1>
</body>
</html>
```

### CSS

```css
.greeting {
    font-weight: bold;
    color: #336699;
    padding: 1rem 2rem;
}

.greeting:hover {
    text-decoration: underline;
}
```

### JSON

```json
{
    "name": "example",
    "version": "1.0.0",
    "dependencies": {
        "foo": "^2.0.0",
        "bar": "~1.2.3"
    }
}
```

### YAML

```yaml
name: example
version: 1.0.0
dependencies:
  foo: ^2.0.0
  bar: ~1.2.3
scripts:
  - build
  - test
```

### SQL

```sql
CREATE TABLE editions (
    code         TEXT PRIMARY KEY,      -- 'en', 'es', 'de'
    name         TEXT NOT NULL,         -- localised name
    release_year INTEGER,
    card_count   INTEGER,
    notes        TEXT
);

CREATE INDEX idx_editions_code ON editions(code);

SELECT e.name, COUNT(*) AS n
FROM editions e
JOIN cards c ON c.edition_code = e.code
WHERE e.release_year >= 2020
GROUP BY e.name
ORDER BY n DESC;
```

### No language (generic)

```
plain code, no language declared
should render in a box with no title, still force-wrapped on long lines
```

A second no-language block to verify the generic banner still closes
cleanly when followed by regular text:

```
one
two
three
```

### Force-wrap of long code lines

```js
const reallyLongVariableName = computeSomethingWithALongFunctionName(firstArgument, secondArgument, thirdArgument, fourthArgument, fifthArgument);
```

---

## Edge cases

A paragraph immediately followed by a code fence (no blank line):
```python
print("fence right below paragraph")
```

An HR followed immediately by a heading:

---
## Right after HR

Table immediately followed by code:

| A   | B   |
| --- | --- |
| 1   | 2   |
```yaml
right: after
table: true
```

Inline code with special chars: `a | b`, `foo --- bar`, `#hash`, `*asterisk*`.

Empty code block:

```
```

## Regression cases

Strikethrough must show a line: ~~struck text~~, and ~~struck with **bold** inside~~.

Code is literal: `__init__`, `ls *.py *.md`, `a ~~b~~ c`.

Escapes stay literal: \*not italic\*, \_not italic\_, \~\~not struck\~\~.

### Heading with **bold** and a long tail that should wrap across several visual lines when the pane is narrow

# Learn C#

- A long bullet item whose text must wrap and keep a hanging indent so the continuation lines align under the text, not under the dash
  1. A nested ordered item that also wraps across lines and keeps its continuation aligned under the text after the number marker

    An indented paragraph line that is long enough to wrap and should keep its four-space indentation on every wrapped visual line.

| Pipes | In cells |
| ----- | -------- |
| `a|b` | x \| y   |

```toml
# comment, not a heading
key = "value"
```

````md
```py
print("nested fence")
```
````

End of test file.
