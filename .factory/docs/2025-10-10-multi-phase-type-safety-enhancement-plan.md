# Comprehensive Type Safety Improvement Plan

## Phase 1: Foundation Setup (Immediate)
**Goal**: Establish proper development environment and fix critical blockers

### 1.1 Environment Setup
- Install dependencies: `uv sync`
- Verify Pyright can resolve imports correctly

### 1.2 Critical Infrastructure Fixes
- Fix `app/api/dependencies.py` async generator return types
- Resolve SQLAlchemy Column type handling in `app/services/stats.py`
- Fix sequence vs list return type mismatches across services

### 1.3 Core Algorithm Type Safety
- Add proper type annotations to `app/algorithms/performance.py`
- Fix unknown variable types in performance calculations
- Ensure algorithm interfaces are properly typed

## Phase 2: High-Value Module Enhancement (Week 1-2)
**Goal**: Strengthen type safety in business-critical areas

### 2.1 Services Layer Type Safety
- Fix all SQLAlchemy ORM type issues in `app/services/`
- Add proper return type annotations for all service methods
- Ensure database models have complete type coverage
- Fix Column type handling and conditional expressions

### 2.2 API Layer Type Safety
- Complete type annotations for all API endpoints
- Fix FastAPI dependency injection types
- Ensure request/response models are properly typed
- Add proper error handling types

### 2.3 Riot API Client Type Safety
- Complete type annotations for `app/riot_api/client.py`
- Fix async context manager types
- Ensure API response models are properly typed
- Add proper error handling types for HTTP operations

## Phase 3: Algorithm and Business Logic (Week 2-3)
**Goal**: Ensure core smurf detection algorithms are fully typed

### 3.1 Algorithm Modules
- Complete `app/algorithms/` type annotations
- Fix statistical calculation types (statistics module usage)
- Ensure data class field types are accurate
- Add proper type guards for algorithm inputs

### 3.2 Data Processing Pipeline
- Fix `app/riot_api/data_manager.py` types
- Ensure data transformation functions are typed
- Add proper type safety for data validation
- Complete caching layer types

### 3.3 Database Integration
- Complete `app/models/` type annotations
- Fix Alembic migration types
- Ensure database session types are consistent
- Add proper type safety for database operations

## Phase 4: Testing and Validation (Week 3-4)
**Goal**: Re-enable test type checking and improve test coverage

### 4.1 Test Type Safety
- Add tests back to Pyright configuration
- Fix test type annotations and mocking types
- Ensure test utilities are properly typed
- Add type checking to CI/CD pipeline

### 4.2 Type Stub Management
- Create custom stubs for problematic third-party packages
- Monitor `reportMissingTypeStubs` warnings
- Add stubs to `typings/` directory as needed
- Consider contributing stubs upstream

### 4.3 Quality Assurance
- Add Pyright to pre-commit hooks
- Set up IDE integration for real-time feedback
- Establish type coverage metrics
- Create type safety guidelines for future development

## Phase 5: Advanced Type Features (Week 4+)
**Goal**: Leverage advanced typing features for maximum safety

### 5.1 Enhanced Strictness
- Expand strict directories to include more modules
- Promote unknown-type warnings to errors gradually
- Add protocol-based typing where appropriate
- Implement generic types for reusable components

### 5.2 Performance and Monitoring
- Add type checking performance monitoring
- Optimize type checking configuration for speed
- Set up type error tracking and reporting
- Create dashboards for type safety metrics

### 5.3 Documentation and Training
- Document type safety practices for the team
- Create type annotation guidelines
- Set up code review checklists for type safety
- Provide training on advanced typing features

## Success Metrics
- Reduce type errors from 376 to <50
- Increase type coverage in strict directories to >95%
- Achieve zero critical type errors in production code
- Maintain <5 minute type checking times
- Integrate type checking into CI/CD pipeline

## Rollout Strategy
- Each phase builds upon the previous one
- Focus on highest-impact areas first
- Maintain backward compatibility
- Provide clear documentation at each step
- Monitor and adjust based on team feedback