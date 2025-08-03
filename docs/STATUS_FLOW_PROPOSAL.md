# Status Flow Implementation Proposal

## 📊 **Forward Flow Table (Normal Development)**

| Stage | Current Status | Event Trigger | Next Status | Description |
|-------|----------------|---------------|-------------|-------------|
| 1 | DISCUSSION | Branch created with issue# | TODO | Developer creates feature branch |
| 2 | TODO | First commit on issue branch | IN PROGRESS | Active development begins |
| 3 | IN PROGRESS | PR opened | PULL REQUEST | Code ready for review |
| 4 | PULL REQUEST | PR merged | DONE | Code accepted and merged |
| 5 | DONE | Release detected | RELEASED | Feature shipped to users |

## 🔄 **Backward Flow Table (Rework/Activity)**

| Current Status | Activity Trigger | Backward Status | Description |
|----------------|------------------|-----------------|-------------|
| PULL REQUEST | Comment on open PR | IN PROGRESS | Developer responds to feedback |
| PULL REQUEST | @mention on open PR | IN PROGRESS | Maintainer requests changes |
| PULL REQUEST | PR review comment | IN PROGRESS | Code review feedback received |
| **IN PROGRESS** | **Push to PR branch** | **PULL REQUEST** | **Developer pushes fixes** |

## 🏪 **Practical Example 1: E-commerce Shopping Cart**

### **Repository**: `shopify/storefront-api`
### **Issue**: #1650 "Add persistent shopping cart functionality"

#### **Forward Flow Journey:**
```
Day 1: DISCUSSION
- User comments on issue #1650: "I can implement cart persistence using localStorage"

Day 2: TODO  
- User creates branch: `feature-1650-cart-persistence`
- System detects branch with issue number → Status: TODO

Day 3: IN PROGRESS
- User commits: "Add cart state management"
- First commit on issue branch → Status: IN PROGRESS

Day 5: PULL REQUEST
- User opens PR #1933: "Implement persistent shopping cart"
- PR opened from feature branch → Status: PULL REQUEST

Day 8: IN PROGRESS (Backward Flow)
- Maintainer comments: "Please add unit tests for cart persistence"
- Comment on open PR → Status: IN PROGRESS

Day 9: PULL REQUEST (Backward Flow)
- User pushes: "Add cart persistence tests" 
- Push to PR branch → Status: PULL REQUEST

Day 10: DONE
- Maintainer merges PR #1933
- PR merged → Status: DONE

Day 20: RELEASED
- Shopify releases v3.2.0 with cart feature
- Release detected → Status: RELEASED
```

#### **Status Transitions:**
```
DISCUSSION → TODO → IN PROGRESS → PULL REQUEST → IN PROGRESS → PULL REQUEST → DONE → RELEASED
```

## 🛠️ **Practical Example 2: Database Migration Tool**

### **Repository**: `prisma/prisma`  
### **Issue**: #2301 "Fix migration rollback mechanism"

#### **Forward Flow Journey:**
```
Day 1: DISCUSSION
- User comments on issue #2301: "The rollback fails when foreign keys exist"

Day 1: TODO
- User creates branch: `fix-2301-rollback-foreign-keys`
- Branch created with issue number → Status: TODO

Day 2: IN PROGRESS  
- User commits: "Analyze foreign key constraints in rollback"
- First commit on issue branch → Status: IN PROGRESS

Day 4: PULL REQUEST
- User opens PR #1939: "Fix migration rollback with foreign keys"
- PR opened → Status: PULL REQUEST

Day 6: IN PROGRESS (Backward Flow)
- Maintainer reviews: "@ramanathan1504 can you add integration tests?"
- @mention on open PR → Status: IN PROGRESS

Day 7: IN PROGRESS (Backward Flow)  
- User gets review comment: "Consider edge case with circular references"
- PR review comment → Status: IN PROGRESS

Day 8: PULL REQUEST (Backward Flow)
- User pushes: "Add integration tests and handle circular refs"
- Push to PR branch → Status: PULL REQUEST

Day 10: DONE
- Maintainer merges PR #1939
- PR merged → Status: DONE

Day 15: RELEASED
- Prisma releases v4.1.1 with rollback fix
- Release detected → Status: RELEASED
```

#### **Status Transitions:**
```
DISCUSSION → TODO → IN PROGRESS → PULL REQUEST → IN PROGRESS → PULL REQUEST → DONE → RELEASED
```

## 🎯 **Key Implementation Points**

### **Forward Flow Triggers:**
1. **Branch Detection**: Parse branch names for issue patterns (`fix-1650-*`, `feature-2301-*`)
2. **First Commit**: Detect initial commit on issue-numbered branch
3. **PR Creation**: Link PR to branch and issue number
4. **Merge Detection**: Check PR merged status
5. **Release Detection**: Monitor repo releases for merged code

### **Backward Flow Triggers:**
1. **PR Activity**: Comments, mentions, reviews on open PRs
2. **Status Priority**: Activity on open PR overrides current status temporarily
3. **Code Updates**: Push events to PR branch move back to review state
4. **Cycle Support**: Allow multiple IN PROGRESS ↔ PULL REQUEST cycles

### **Status Priority Logic:**
```
1. MERGED (highest priority) → DONE
2. RELEASED → RELEASED  
3. OPEN PR + ACTIVITY → IN PROGRESS
4. OPEN PR → PULL REQUEST
5. COMMITS ON BRANCH → IN PROGRESS
6. BRANCH CREATED → TODO
7. COMMENT ONLY → DISCUSSION
```

## 🔧 **Implementation Requirements**

### **New Detection Capabilities Needed:**
1. **Branch Name Parsing**: Extract issue numbers from branch names
2. **Commit Analysis**: Track first commit on issue branches  
3. **PR-Branch Linking**: Connect PRs to their source branches
4. **Activity Context**: Distinguish between PR activity vs general activity
5. **Push Target Detection**: Identify pushes to PR branches vs other branches

### **Enhanced Event Processing:**
1. **PushEvent**: Check if push is to PR branch or issue branch
2. **PR Events**: Link PR number to source branch and issue
3. **Comment Events**: Detect if comment is on open PR vs closed/merged PR
4. **Review Events**: Process review comments with PR context

This proposal provides the complete bidirectional flow with realistic examples showing how development work naturally cycles between IN PROGRESS and PULL REQUEST states based on feedback and updates.
